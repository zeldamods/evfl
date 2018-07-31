import enum

class DataType0(enum.IntEnum):
    kInt = 0
    kFloat = 1
    kString = 2
    kWString = 3
    kStream = 4

class QueryValueType(enum.IntEnum):
    kBool = 0
    kInt = 1
    kFloat = 2
    kString = 3
    kConst = 4

class DataType1(enum.IntEnum):
    kInt = 0
    kBool = 1
    kFloat = 2
    kString = 3
    kWString = 4

class EventType(enum.IntEnum):
    kAction = 0
    kSwitch = 1
    kFork = 2
    kJoin = 3
    kSubFlow = 4

class ContainerDataType(enum.IntEnum):
    kArgument = 0
    kContainer = 1
    kInt = 2
    kBool = 3
    kFloat = 4
    kString = 5
    kWString = 6
    kIntArray = 7
    kBoolArray = 8
    kFloatArray = 9
    kStringArray = 10
    kWStringArray = 11
    kActorIdentifier = 12

class TriggerType(enum.IntEnum):
    kFlowchart = 0
    kClipEnter = 1
    kClipLeave = 2
    kOneshot = 3
    kNormal = 0
    kEnter = 1
    kLeave = 2

class TimelineState(enum.IntEnum):
    kNotStarted = 0
    kPlaying = 1
    kStop = 2
    kPause = 3

class State(enum.IntEnum):
    kInvalid = 0
    kFree = 1
    kNotInvoked = 2
    kInvoked = 3
    kDone = 4
    kWaiting = 5

class BuildResultType(enum.IntEnum):
    kSuccess = 0
    kInvalidOperation = 1
    kResFlowchartNotFound = 2
    kEntryPointNotFound = 3
