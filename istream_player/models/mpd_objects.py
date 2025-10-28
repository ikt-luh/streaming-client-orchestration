from dataclasses import dataclass
from typing import Dict, Literal, Optional, Union


class MPD(object):
    def __init__(
        self,
        content: str,
        url: str,
        type_: Literal["static", "dynamic"],
        media_presentation_duration: float,
        max_segment_duration: float,
        min_buffer_time: float,
        adaptation_sets: Dict[int, "AdaptationSet"],
        attrib: Dict[str, str]
    ):
        self.content = content
        """
        The raw content of the MPD file
        """

        self.url = url
        """
        The URL of the MPD file
        """

        self.type: Literal["static", "dynamic"] = type_
        """
        If this source is VOD ("static") or Live ("dynamic")
        """

        self.media_presentation_duration = media_presentation_duration
        """
        The media presentation duration in seconds
        """

        self.min_buffer_time = min_buffer_time
        """
        The recommended minimum buffer time in seconds
        """

        self.max_segment_duration = max_segment_duration
        """
        The maximum segment duration in seconds
        """

        self.adaptation_sets: Dict[int, AdaptationSet] = adaptation_sets
        """
        All the adaptation sets
        """

        self.attrib = attrib
        """
        All attributes from XML
        """


class AdaptationSet(object):
    def __init__(
        self,
        adaptation_set_id: int,
        content_type: Literal["video", "audio", "pointcloud"],
        frame_rate: Optional[str],
        max_width_or_x: Union[int, float],
        max_height_or_y: Union[int, float],
        par: Optional[str],
        representations: Dict[int, "Representation"],
        attrib: Dict[str, str],
        max_z_pos: float = 0,
        max_x_rot: float = 0,
        max_y_rot: float = 0,
        max_z_rot: float = 0
    ):
        self.id = adaptation_set_id
        """
        The adaptation set id
        """

        self.content_type: str = content_type
        """
        The content type of the adaptation set. It could be "video", "audio", or "pointcloud"
        """

        self.frame_rate: Optional[str] = frame_rate
        """
        The frame rate string
        """

        # For backward compatibility and pointcloud support
        if content_type == "pointcloud":
            self.max_x_pos: float = float(max_width_or_x)
            self.max_y_pos: float = float(max_height_or_y)
            self.max_z_pos: float = max_z_pos
            self.max_x_rot: float = max_x_rot
            self.max_y_rot: float = max_y_rot
            self.max_z_rot: float = max_z_rot
            # For compatibility, set width/height to 0
            self.max_width: int = 0
            self.max_height: int = 0
        else:
            self.max_width: int = int(max_width_or_x)
            self.max_height: int = int(max_height_or_y)
            # For compatibility, set pointcloud params to 0
            self.max_x_pos: float = 0
            self.max_y_pos: float = 0
            self.max_z_pos: float = 0
            self.max_x_rot: float = 0
            self.max_y_rot: float = 0
            self.max_z_rot: float = 0

        self.par: Optional[str] = par
        """
        The ratio of width / height (not applicable for pointclouds)
        """

        self.representations: Dict[int, Representation] = representations
        """
        All the representations under the adaptation set
        """

        self.attrib = attrib
        """
        All attributes from XML
        """


class Representation(object):
    def __init__(
        self,
        id_: int,
        mime_type: str,
        codecs: str,
        bandwidth: int,
        width_or_x: Union[int, float],
        height_or_y: Union[int, float],
        initialization: str,
        segments: Dict[int, "Segment"],
        attrib: Dict[str, str],
        z_pos: float = 0,
        x_rot: float = 0,
        y_rot: float = 0,
        z_rot: float = 0
    ):
        self.id = id_
        """
        The id of the representation
        """

        self.mime_type = mime_type
        """
        The mime type of the representation
        """

        self.codecs: str = codecs
        """
        The codec string of the representation
        """

        self.bandwidth: int = bandwidth
        """
        Average bitrate of this stream in bps
        """

        # Determine if this is a pointcloud based on attributes or mime type
        is_pointcloud = ('x_pos' in attrib or 'xPos' in attrib or 
                        'pointcloud' in mime_type.lower() or
                        z_pos != 0 or x_rot != 0 or y_rot != 0 or z_rot != 0)

        if is_pointcloud:
            self.x_pos: float = float(width_or_x)
            self.y_pos: float = float(height_or_y)
            self.z_pos: float = z_pos
            self.x_rot: float = x_rot
            self.y_rot: float = y_rot
            self.z_rot: float = z_rot
            # For compatibility, set width/height to 0
            self.width: int = 0
            self.height: int = 0
        else:
            self.width: int = int(width_or_x)
            self.height: int = int(height_or_y)
            # For compatibility, set pointcloud params to 0
            self.x_pos: float = 0
            self.y_pos: float = 0
            self.z_pos: float = 0
            self.x_rot: float = 0
            self.y_rot: float = 0
            self.z_rot: float = 0

        self.initialization: str = initialization
        """
        The initialization URL
        """

        self.segments: Dict[int, Segment] = segments
        """
        The video segments
        """

        self.attrib = attrib
        """
        All attributes from XML
        """


@dataclass
class Segment(object):
    # Segment URL
    url: str

    # Stream Initilalization URL
    init_url: str

    # Segment play duration in seconds
    duration: float

    # Segment play start time
    start_time: float

    # Adaptation Set ID
    as_id: int

    # Representation ID
    repr_id: int