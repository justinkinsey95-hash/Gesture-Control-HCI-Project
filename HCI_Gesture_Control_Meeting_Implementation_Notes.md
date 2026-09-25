# HCI Gesture-Control Project --- Meeting & Implementation Notes

## Current Implementation Direction

The project uses computer vision and hand tracking to recognize gestures
and translate them into computer actions. The immediate focus is
reliable **swipe-up and swipe-down detection**, eventually allowing a
user to scroll without touching a keyboard or mouse. A recipe website
remains an important demonstration scenario because a user could
navigate a webpage while their hands are occupied or dirty.

An important design direction discussed by the team is putting some
responsibility on the **user's gesture technique**, rather than trying
to make the software interpret every possible hand movement. A smaller,
well-defined gesture vocabulary with clear starting and ending
conditions may make the system more reliable and easier for users to
learn.

## 1. Project Assignments and Team Workflow

The team is collaboratively responsible for defining the project's
features, evaluating usability, testing the prototype, documenting
design decisions, and identifying improvements. During weekly Discord
meetings, team members discuss the current implementation, problems
discovered during testing, possible solutions, and which ideas are
realistic within the project's scope.

One challenge has been dividing a relatively focused prototype into
meaningful individual assignments for a six-person team. Creating
separate implementation features simply to give every member an
independent programming task could introduce redundant work or
unnecessary **scope creep**. Because of this, the team is continuing to
identify contributions that support the core project without expanding
its scope solely for the purpose of dividing work.

The current workflow allows members to contribute through feature
research, gesture and interaction design, usability evaluation, testing,
documentation, lo-fi prototype work, and implementation. When a proposed
feature requires integration into the existing codebase, Justin can help
implement or integrate the team's documented requirements and findings.
This allows technical development to remain coordinated while still
incorporating decisions and work produced collaboratively by the group.

Weekly meetings are especially important to this process. They allow the
team to review what has been implemented, test assumptions, identify
problems, decide which ideas are worth pursuing, and generate more
specific tasks for the next stage of development.

### Current Features and Tasks Under Consideration

**Swipe hold/cooldown.** The current swipe behavior can produce an
unintended opposite gesture. For example, after intentionally swiping
down, returning the index finger toward its resting position may
resemble a swipe up. The team discussed having the gesture enter a
temporary **hold or cooldown state** after recognition. During that
state, little or no relevant landmark movement would need to occur
before another swipe can register. This could reduce accidental repeated
or opposite inputs without continually adding increasingly complicated
constraints to swipe detection.

**Open-palm starting position.** The current system includes a
requirement related to holding the hand still, but this may not
constrain the starting state enough. The team proposed requiring an
**open palm facing approximately toward the camera**, similar to
offering someone a high five, before a gesture can begin. The user would
therefore have a clearer responsibility for entering a recognizable
starting pose. This may simplify gesture recognition and make the
interaction more predictable.

**Website pop-ups.** Recipe sites frequently display advertisements,
subscription prompts, cookie notices, and other pop-ups. These may
interfere with the intended interaction or change which window or
element has focus. One proposed additional gesture would issue an
**Escape (`Esc`) key input** to dismiss compatible pop-ups. A possible
gesture discussed was forming an **O shape with the hand**, although the
gesture itself has not been finalized.

**Browser compatibility.** The team wants to determine whether
computer-input behavior depends specifically on Chrome or whether it
works with other browsers and applications. This should be tested and
documented so that the prototype does not unintentionally depend on one
team member's particular browser setup.

**Camera differences.** Webcam resolution, frame rate, image quality,
lighting, and hardware may affect tracking and gesture recognition. The
team does not currently plan to design around every possible webcam, but
testing the prototype on different team members' devices could help
determine how dependent the system is on a particular camera or
environment.

**"Jump to Recipe" concept --- exploratory/out of scope.** The team
discussed whether the application could identify a website control such
as **"Jump to Recipe"** and activate it. Automatically understanding
arbitrary webpage buttons would significantly broaden the project
because the application would have to determine which page element is
relevant. A more constrained demonstration might target a **known HTML
element or identifier on a predetermined webpage**. The team considers
this an interesting possible extension, but it is not currently a
committed feature.

## 2. Risks

**Gesture ambiguity** is currently one of the clearest technical risks.
A legitimate movement back toward the user's resting position can
accidentally resemble another gesture. Recognition therefore has to
balance sensitivity against excessive restrictions. Too little
restriction can cause false inputs, while too much could make gestures
difficult or frustrating to perform.

**Hardware and environmental differences** are another risk. Camera
quality, frame rate, positioning, lighting, and background conditions
could affect MediaPipe's ability to track the hand consistently. Testing
across team members' devices can help determine the severity of this
issue.

**Website and application behavior** may introduce unexpected problems.
Pop-ups, advertisements, focus changes, and differences between browsers
could interfere with scrolling or keyboard inputs generated by the
application.

**Scope creep** is an important project-management risk. Ideas such as
interpreting webpage HTML, recognizing additional gestures, or adding
more computer controls could expand the project beyond its central
objective. The team will need to distinguish between features necessary
for the core demonstration and features that would simply be interesting
to add.

**Task distribution** is also a project-management challenge. Because
the prototype has a deliberately focused scope and the team has six
members, dividing the project into independent technical components can
create redundant work or encourage unnecessary features. The team will
need to continue identifying meaningful assignments in areas such as
testing, interaction design, documentation, prototyping, research, and
implementation rather than measuring contribution only through separate
coding tasks.

## 3. Hardware / Software Needs

The prototype requires a computer with a webcam and the project's Python
development environment. The current implementation uses **OpenCV** for
camera/video processing and **MediaPipe** for hand and landmark
tracking. Additional software functionality is used to translate
recognized gestures into computer inputs.

A web browser and applications capable of responding to simulated
keyboard or scrolling inputs are required for demonstrations. Recipe
websites are currently an important demonstration environment.

A major advantage of the project's approach is that it does **not
require specialized gesture-control hardware**. An ordinary webcam is
intended to provide the necessary input. However, testing with different
webcams and computers will help determine how portable the prototype
actually is.

The team also uses **Git/GitHub** to maintain the project's code and
support collaboration, while **Discord** provides the primary
environment for weekly team communication.

## 4. Project Monitoring and Reporting

The team currently meets **weekly through Discord**. These meetings
serve as more than simple progress reports. They provide an opportunity
for members to review the current prototype, discuss implementation
progress, identify usability problems and blocking issues, evaluate
proposed features, and determine what work should happen next.

This communication is particularly important because meaningful task
distribution has been an ongoing challenge. Rather than creating
unnecessary features solely to divide programming work among six people,
meetings allow the team to identify useful contributions as needs emerge
from the prototype.

The team can therefore use a repeating process throughout development:

**Implement/prototype → test → discuss findings as a team → identify
problems and priorities → assign specific work → implement the next
iteration.**

GitHub provides a shared location for maintaining the implementation and
tracking changes to the codebase. Discord provides the primary
communication environment for discussing progress and making
collaborative decisions.

## Feature Scope Summary

For planning purposes, the ideas discussed by the team can currently be
separated into three levels of commitment:

  -----------------------------------------------------------------------
  Category                            Current Features / Ideas
  ----------------------------------- -----------------------------------
  **Core project**                    Hand tracking, swipe-up/down
                                      recognition, computer interaction,
                                      recipe-site demonstration

  **Candidate improvements**          Swipe cooldown/hold, open-palm
                                      start, Escape/pop-up gesture,
                                      cross-browser testing, cross-camera
                                      testing

  **Exploratory / future**            Reading or targeting webpage
                                      elements such as "Jump to Recipe"
  -----------------------------------------------------------------------

This distinction is important because **not every idea generated during
team meetings needs to become an implemented feature**. The team's
priority is producing a reliable gesture-control prototype rather than
increasing the number of features simply because they are technically
possible.
