from collections import namedtuple
import webrtcvad
import numpy as np


VadObject = namedtuple("VadObject", ["time_section", "channel", "frame", "is_chunk_end"])


class TimeSection:
    def __init__(self, t_start, t_end):
        self.__t_start = t_start
        self.__t_end = t_end

    def __str__(self):
        return " ".join(["Vad chunk start", str(self.__t_start), "vad chunk end", str(self.__t_end)])

    @property
    def t_start(self):
        return self.__t_start

    @property
    def t_end(self):
        return self.__t_end


class ChannelMeta:
    def __init__(self, prev_value, t_start, t_end, vadder):
        self.__prev_value = prev_value
        self.t_start = t_start
        self.t_end = t_end
        self.vadder = vadder
        self.prev_speech_frame = np.empty(0)
        self.sample_rate = None
        self.shift = 0

    @property
    def prev_value(self):
        return self.__prev_value

    @prev_value.setter
    def prev_value(self, value):
        self.__prev_value = value
        # print(self.channel)

    def __str__(self):
        return " ".join([str(self.prev_value), str(self.t_start), str(self.t_end)])


class VadGenerator:
    def __init__(self, num_channels, frame_duration=10, vad_mode=3, concat_threshold=0.5,
                  speech_duration=0.5):

        """
        Generator of vad objects from numpy array in range form -1 to 1 with sound.
        Leave only speech fragments from sound.
        In case length of silence is less than concat_threshold (in seconds)
        segments of speech are merged.
        Leaves only speech fragments with lengths longer than speech_duration (in seconds).
        Can work with sequence of consecutive sound fragments.
        """
        self.channel_mapping = []
        self.frame_duration = frame_duration
        self.num_channels = num_channels
        self.concat_threshold = concat_threshold
        self.speech_duration = speech_duration
        for channel in range(num_channels):
            vadder = webrtcvad.Vad()
            vadder.set_mode(vad_mode)
            self.channel_mapping.append(ChannelMeta(None, -1, 0, vadder))

    def emit(self, frame, sample_rate):
        """
        Yields sound chunks from frame. Store information about current last speech fragment to work with
        streaming frames.
        """
        sample_rate = int(sample_rate)
        step = int(self.frame_duration * sample_rate // 1000)
        num_channels = frame.shape[-1]
        speech_flag_by_channels = {channel : False for channel in range(num_channels)}
        if num_channels != self.num_channels:
            raise ValueError("Wrong number of channels")
        timestamps_threshold = self.concat_threshold * sample_rate
        speech_threshold = self.speech_duration * sample_rate
        for index in range(0, len(frame) - step, step):
            for channel in range(num_channels):
                bytes_frame = np.array(frame[index: index + step, channel] * 32768,
                                       dtype=np.int16).tobytes()
                channel_meta = self.channel_mapping[channel]
                shift = channel_meta.shift
                prev_speech_frame = channel_meta.prev_speech_frame
                cur_value = channel_meta.vadder.is_speech(bytes_frame, sample_rate)
                if cur_value:
                    speech_flag_by_channels[channel] = True
                if cur_value != channel_meta.prev_value:
                    channel_meta.prev_value = cur_value
                    if not cur_value and index > 0:
                        channel_meta.t_end = index + shift
                    elif cur_value:
                        t_start = channel_meta.t_start
                        t_end = channel_meta.t_end
                        if t_start >= shift:
                            if index + shift - t_end > timestamps_threshold:
                                next_frame = frame[t_start - shift: t_end - shift, channel]
                                if len(next_frame) > speech_threshold:
                                    yield VadObject(TimeSection(t_start / sample_rate,
                                                        t_end / sample_rate), channel, next_frame, False)
                                channel_meta.t_start = index + shift
                        else:
                            if t_start < 0:
                                channel_meta.t_start = index + shift
                            elif index + shift - t_end > timestamps_threshold:
                                if t_end > shift:
                                    next_frame = np.concatenate([prev_speech_frame, frame[: t_end - shift, channel]])
                                else:
                                    next_frame = channel_meta.prev_speech_frame[: t_end - t_start]
                                if len(next_frame) > speech_threshold:
                                    yield VadObject(TimeSection(t_start / sample_rate,
                                                                t_end /sample_rate), channel, next_frame, False)
                                channel_meta.t_start = index + shift
                                channel_meta.prev_speech_frame = np.empty(0)

        # last speech frame
        for channel in range(num_channels):
            channel_meta = self.channel_mapping[channel]
            t_start = channel_meta.t_start
            shift = channel_meta.shift
            if t_start >= shift:
                channel_meta.prev_speech_frame = frame[t_start - shift:, channel]
            elif speech_flag_by_channels[channel]:
                channel_meta.prev_speech_frame = np.concatenate([channel_meta.prev_speech_frame,
                                                                 frame[:, channel]])
            else:
                prev_speech_frame = channel_meta.prev_speech_frame
                t_start = (shift - len(prev_speech_frame)) / sample_rate
                t_end = shift / sample_rate
                if len(prev_speech_frame) > speech_threshold:
                    yield VadObject(TimeSection(t_start, t_end), channel, prev_speech_frame, True)
                channel_meta.prev_speech_frame = np.empty(0)
                channel_meta.t_start = -1
            channel_meta.sample_rate = sample_rate
            channel_meta.shift += len(frame)

    def emit_last(self):
        """
        Yields last speech fragment if there are no following frames.
        """
        for channel in range(self.num_channels):
            channel_meta = self.channel_mapping[channel]
            next_frame = channel_meta.prev_speech_frame
            sample_rate = channel_meta.sample_rate
            if len(next_frame) > self.speech_duration * sample_rate and channel_meta.t_start > 0:
                yield VadObject(TimeSection(channel_meta.t_start / sample_rate,
                                            channel_meta.shift / sample_rate),
                                            channel, next_frame, True)