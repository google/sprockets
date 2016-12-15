# State Transition Language
*Last updated at 2016-12-05*

## 1. Introduction
**State Transition Language** (STL) is a modular programming language to represent a system defined with a set of protocols (or specifications). Each module may define one or more protocols or part of one protocol.

A protocol specification describes the behavior of entities in a given system and their interactions. Since entities behave differently depending on their state, a system can be represented as a finite state machine where a state consists of the combination of all entities’ states, and events incoming and outgoing are the interactions of entities.

STL is used to define states and their transitions to other states when some events happen. A **module** of STL consists of

* **Roles** representing individual entities in a system
* **States**, a detailed state of a system. A global state of a system consists of one or more detailed states
* **Transitions** from a system state to another system state
* **Events**, interactions among roles. State transitions are triggered by events
* **Messages** representing data of events
* **Qualifiers** for generating/validating protocol message fields

## 2. Example code
```
module example;

// Constants
//
const string kHelloWorld = "Hello, World!";

// Roles
//
role rSender {
  string ipAddress;
  string transportId;
}

role rReceiver {
  string ipAddress;
  string transportId;
}

// States
//
state sTlsState(int tlsId) {
  kNotConnected,
  kConnected,
}

// Messages
//
message mSimpleMessage {
  encode "json";
  required string words;
}

message[] mMessageArray {
  encode "json";
  required int i;
}

message mProtoMessage {
  encode "protobuf";
  external "proto.example_pb2.SimpleMsg";
}

message mMessageWithData {
  encode "json";

  required int request_id;
  required string data;
  optional string optional_data;
  repeated string optional_repeated_data;
  optional mNestedMessage optional_nested_data;

  message mNestedMessage {
    required string data;
  }
}

// Qualifiers
//
qualifier int UniqueInt(int prev) = external "stl.lib.UniqueInt";

// Events
//
event Sleep(int tlsId) = external "noop.Sleep";
event LogParams(mSimpleMessage msg) = external "noop.LogParams";
event LogEncodedParams(mMessagearray msg) = external "noop.LogEncodedParams";

event SendRequest(int& requestId, string data) =
    LogEncodedParams(mMessageWithData {
                       request_id = UniqueInt(requestId) -> requestId;
                       data = data;
                     });

event SendResponse(int requestId, string data) =
    LogEncodedParams(mMessageWithData {
                       request_id = requestId;
                       data = data;
                     });


// Transitions
//
transition tConnectTls(int tlsId) {
  pre_states = [ sTlsState(tlsId).kNotConnected ]
  events {
    rSender -> Sleep(tlsId) -> rReceiver;
  }
  post_states = [ sTlsState(tlsId).kConnected ]
}

transition tDisconnectTls(int tlsId) {
  pre_states = [ sTlsState(tlsId).kConnected ]
  events {
    rSender -> LogParams(mSimpleMessage { words = kHelloWorld; }) -> rReceiver;
    rSender -> LogEncodedParams(mMessageArray [{ i = 600; }, {i = 30;}]) -> rReceiver;
    rSender -> LogEncodedParams(mProtoMessage {
                                  foo = mMessageArray [{ i = 13; }, { i = 14;}];
                                  fizz = 12345;
                                  buzz = [true, true, false];
                                }) -> rReceiver;
  }
  post_states = [ sTlsState(tlsId).kNotConnected ]
}

transition tRequestResponse(int tlsId) {
  int requestId;
  pre_states = [ sTlsState(tlsId).kConnected ]
  events {
    rSender -> SendRequest(&requestId, "REQUEST") -> rReceiver;
    rReceiver -> SendResponse(requestId, "RESPONSE") -> rSender;
  }
  post_states = []
}


transition tConnectTlsActual = tConnectTls(1);
transition tDisconnectTlsActual = tDisconnectTls(1);
transition tRequestResponseActual = tRequestResponse(1);
```

## 3. Modules
A STL file begins with a module definition. A **module** is similar to namespace in C++ or package in Java and Python.
```
module example;
```
All names are defined within a module.

## 4. States
A system consists of states. A **state** has a value representing a situation of the whole system that affects the system’s behavior for subsequent events and eventually may change its value.

*Note: if a value doesn’t affect the state transition, it should not be a state since it just adds complexity of state transition specification.*

A state definition may have parameters which are used to populate actual states by assigning values to parameters during state transitions. 
```
state sTlsState(int tlsId) {
  kNotConnected,
  kConnected,
}
```

## 5. Roles
A **role** is a conceptual object interacting with other roles by sending and receiving events. A role may have internal variables to store values temporarily which don’t affect states.

*Note: any variables which may affect state transition must not be stored in roles’ variables, but be defined as states.*

A role represents an individual actual entity of the system and cannot have parameters.

*Note: Maybe it might be useful for role to have parameters. But, it seems hard to specify what roles should be tested in the manifest file.*
```
role rSender {
  string ipAddress;
  string transportId;
}
```

## 6. Events
An **event** is an interaction between two roles. It must be visible which means it must be caught and tested somehow. Typically, an event represents an action for a role (source) to send message to another role (target). Source role and target role can be same.

An event is takes one of three forms: an external event; a user-defined event which can be implemented by another event; or empty (no-op).

A user-defined event may have parameters that are used to populate actual events by assigning values to parameter during state transitions. 
```
event SendResponse(int requestId, string data) =
    LogEncodedParams(mMessageWithData {
                       request_id = requestId;
                       data = data;
                     });
```

An external event is defined and provided by the framework running the given STL file.
```
event LogEncodedParams(mMessagearray msg) = external "noop.LogEncodedParams";
```

## 7. Messages
A **message** defines the format of data sent by a role.

A message can be nested with multiple messages, and may have parameters. A message is replaced with actual data encoded accordingly during populating events.

A message consists of one or more fields. A field can be **required**, **optional**, or **repeated**. It is similar to how fields are defined in [protocol buffer](https://developers.google.com/protocol-buffers/).
```
message mMessageWithData {
  encode "json";

  required int request_id;
  required string data;
  optional string optional_data;
  repeated string optional_repeated_data;
  optional mNestedMessage optional_nested_data;

  message mNestedMessage {
    required string data;
  }
}
```

A top-level message can specify encoding mechanism with **encode**. Currently, 3 encoding mechanisms are supported: "json", "bytestream", "protobuf". A protobuf message may specify the message defined in proto file with **protobuf_message** instead of listing all fields.
```
message mProtoMessage {
  encode "protobuf";
  external "proto.example_pb2.SimpleMsg";
}
```

A top-level (or not nested) message can be an array of same data format for given encoding mechanism.
```
message[] mMessageArray {
  encode "json";
  required int i;
}
```

## 8. Qualifiers
A **qualifier** is used to both validate and generate values in a message field. One example is a UniqueString qualifier; this qualifier will always generate new and unique strings when an STL message is created. When attempting to validate an externally-generated message, this qualifier will ensure that the string in the qualified message field is unique among all fields which also use this qualifier. Qualifiers can be parameterized and are evaluated at event run-time.

Qualifiers can also be used to write message field values out to local variables in a transition; after either generation or validation, the qualified value can be assigned to a variable for later use. A variable is passed into an event by reference, indicated by the ‘&’ character following the type of an event parameter. The value of a message field can be written to the referenced variable by use of the right arrow ‘->’ operator.
```
qualifier int UniqueInt(int prev) = external "stl.lib.UniqueInt";

event SendRequest(int& requestId, string data) =
    LogEncodedParams(mMessageWithData {
                       request_id = UniqueInt(requestId) -> requestId;
                       data = data;
                     });
```

## 9. State transitions
A **transition** defines what events trigger a transition from a set of states to another set of states.

Comparing to a typical finite state machine which moves from a state to another state on events given from external and outputs other events, STL represents a system and/so all events in STL are internal to the given system and all states in STL are global, but not specific to a role. A state transition can be interpreted as, when the system is in the states defined in **pre_states** and a list of events defined in **events** happen, the system must be regarded to move in the states defined in **post_states**. If any of events defined in **events** failed, the system must be regarded to move in the states defined in **error_states** if defined, or stay in the states in  **pre_states** if **error_states** is not defined.

A state transition can define local variables which are not states, but necessary for parameter values of events.

A state transition may have parameters which will be populated by other state transition with values.
```
transition tDisconnectTls(int tlsId) {
  pre_states = [ sTlsState(tlsId).kConnected ]
  events {
    rSender -> LogParams(mSimpleMessage { words = kHelloWorld; }) -> rReceiver;
    rSender -> LogEncodedParams(mMessageArray [{ i = 600; }, {i = 30;}]) -> rReceiver;
    rSender -> LogEncodedParams(mProtoMessage {
                                  foo = mMessageArray [{ i = 13; }, { i = 14;}];
                                  fizz = 12345;
                                  buzz = [true, true, false];
                                }) -> rReceiver;
  }
  post_states = [ sTlsState(tlsId).kNotConnected ]
}

transition tDisconnectTlsActual = tDisconnectTls(1);
```

### 9.1. pre_states
**pre_states** defines a list of states that the given system must be in to perform the given state transition. It is an AND combination of all states specified in **pre_states**. If a state is not specified, it means the state can be in any value.

A state can be in multiple values, i.e. OR combination for given state.
```
pre_states = [ sState1(param1).kValue1,
               sState2(param2, param3).{kValue2, kValue3} ]
```

### 9.2. events
**events** defines a list of events triggered by a role (the source) and affecting another role (the target). Events are executed sequentially. An event reports whether it succeeded the execution or failed. If it succeeded, the next event starts executing until all events finished. If all events finished successfully, the system is regarded to move in the states defined in **post_states**. If any of events failed, the system is regarded to move in the states defined in **error_states** if defined, or stay in the states in  **pre_states** if not defined.
```
events {
    rSource -> eEvent1(param1) -> rTarget;
    rTarget -> eReturningEvent(param2, param3) -> rSource;
}
```

### 9.3. post_states
**post_states** defines a list of states where the given system must be in when all events specified in **events** finished successfully. It is an AND combination of all states specified in **post_states**. If a state is not specified, it means the state is not changed from the value specified in **pre_states**.

Unlike in **pre_states**, a state in **post_states** cannot be in multiple values.
```
post_states = [ sState1(param1).kValue1,
                sState2(param2, param3).kValue2 ]
```

### 9.4. error_states
**error_states** is optional. If it is specified, it defines a list of states where the given system must be in when any events specified in **events** failed. It is an AND combination of all states specified in **error_states**. If a state is not specified, it means the state is not changed from the value specified in **pre_states**.

Like **post_states**, a state in **error_states** cannot be in multiple values.
```
error_states = [ sState1(param1).kValue1,
                 sState2(param2, param3).kValue2 ]
```

## 10. Types
### 10.1. Integer
Keyword: **int**

Values: Currently only non-negative integers. Values can only contain digits.
```
int myInt = 0;
int myOtherInt = 9001;
```

### 10.2. String
Keyword: **string**

Values: String values enclosed in double quotes (" "). Backslash (\) is used for escaping.
```
string myEmptyString = "";
string mySimpleString = "this is a string";
string myEscapedString = "this is a string with \"escaped quotes\””;
```

### 10.3. Boolean
Keyword: **bool**

Values: **true** or **false**
```
bool myTrueBool = true;
bool myFalseBool = false;
```

## 11. Miscellaneous
### 11.1. Constants
Keyword: **const**

Values: Any Type from above can be a constant by putting **const** before the variable definiton. The variable must be assigned a value in the declaration.
```
const bool kTruth = true;
const int kDozen = 12;
const string kServerUrl = "http://example.com";
```

### 11.2. Comments
Comments are indicated by double forward slash: //

A commnet starts at the // and continues to the end of the line.
```
// This entire line is a comment
// This is another comment.
const int kFoo = 0;  // This comment is only at the end of the line.
```
