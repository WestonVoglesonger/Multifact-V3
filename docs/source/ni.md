# NI_Guidelines.md

## Introduction

This document details how to structure **Narrative Instructions (NIs)** so our system can reliably parse them. The instructions use a bracket-based mini-language for Scenes, Components, and Functions. By following these guidelines, you ensure a consistent, machine-readable format.

---

## 1. Required Bracket Syntax

- **Scene**  
[Scene: <SceneName>]

- **Component**  
[Component: <ComponentName>]

- **Function**  
[Function: <FunctionName>]

**Allowed variations**:  
- A single space after the colon is optional. For example, `[Scene: MyScene]` or `[Scene:MyScene]`.
- Brackets must be on their own line, with **no additional text** following on the same line.

**Not allowed**:  
- Typos in the bracket keyword (e.g., `[Scen: Main]`, `[Components: MyComp]`).
- Extra space before the colon (e.g., `[Scene : MyScene]`).

---

## 2. Hierarchy and Ordering

1. A **Scene** can contain multiple **Components**.  
2. A **Component** can contain multiple **Functions**.  
3. Lines of text **after** a bracket line—until the next bracket line or the end of the document—are assigned to that Scene’s/Component’s/Function’s content.

**Example**:
[Scene: IntroScene] This is the intro scene. The user arrives here first.

[Component: GreetingComp] Contains logic to greet the user.

[Function: doGreeting] Responsible for printing "Hello user!"

Here, **IntroScene** is a scene token, **GreetingComp** is a component token nested within the scene, and **doGreeting** is a function token nested within the component.

---

## 3. Content for Scenes, Components, Functions

After a bracket header, any text on subsequent lines **belongs** to that token until the next bracket header or the end of the document.

For instance:
[Scene: Profile] The Profile scene describes everything about the user’s profile page.

[Component: Avatar] Shows the user’s avatar and display name.

[Function: loadAvatar] Loads the avatar from an external URL Handles any fallback logic if the URL fails.

- **Profile** is the scene name.
- **Avatar** is a component within the Profile scene.
- **loadAvatar** is a function within the Avatar component.

---

## 4. Handling Empty Function Names

If you write `[Function]` without specifying a name, our parser auto-generates a function name (`func_` plus a hash). We recommend naming your functions for clarity:
[Function: handleLogin]

---

## 5. Dependencies (`REF:`)

If your NI references another token or resource, you can include lines like:
REF:SomeOtherComponent

This captures the dependency internally. For example:
[Scene: Cart] REF:Payment

[Component: Payment] ...

Here, the “Cart” scene depends on the “Payment” token.

---

## 6. Example NI

A concise example:
[Scene: Dashboard] This scene is shown after login.

[Component: StatisticsPanel] Displays the user’s activity and recent logs. REF:ChartsModule

[Function: loadData] Makes an API call to fetch stats.

[Function: renderCharts] Uses the retrieved data to render visuals.

[Component: QuickActions] Shortcuts for common tasks.

[Function: createProject] Prompts the user to create a new project.

- **1 Scene**: `Dashboard`
- **2 Components**: `StatisticsPanel`, `QuickActions`
- **3 Functions**: `loadData`, `renderCharts`, `createProject`

---

## 7. Common Mistakes

1. **Extra space before the colon**  
   - **Incorrect**:  
     ```
     [ Scene: Intro ]
     [Scene : Intro]
     ```
   - **Correct**:  
     ```
     [Scene: Intro]
     ```
2. **Bracket text plus extra text on the same line**  
   - **Incorrect**:  
     ```
     [Function: doGreeting] code after bracket
     ```
   - **Correct**:  
     ```
     [Function: doGreeting]
     code in the next lines
     ```
3. **Misordered nesting** or placing bracket headers incorrectly. Scenes can have multiple Components, which can have multiple Functions. While our parser accommodates many variations, it’s best to group tokens logically.

---

## 8. Summary

- Place **one** bracket header (Scene/Component/Function) **per line**.
- All subsequent lines until the next bracket belong to that bracket token.
- Keyword spelling is crucial: `Scene`, `Component`, `Function` (case-insensitive but spelled correctly).
- `REF:Name` lines indicate dependencies (optional).
- Name your functions if possible (`[Function: doGreeting]` vs. `[Function]`).
- Following these patterns ensures consistent tokenization and reliable code generation.
