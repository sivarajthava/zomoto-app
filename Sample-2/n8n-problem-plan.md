# Problem Statement — AI Weather Agent

## 1. Overview

Build a **single AI-agent workflow using n8n** that allows a user to ask for the weather of a location using natural language.

The AI agent should understand the location mentioned in the user's prompt, retrieve the current weather information for that location from a weather API, and provide a clear response to the user.

The solution should demonstrate how an AI agent can understand natural-language input, extract the required location, call an external weather service, and present the result conversationally.

---

## 2. Problem

Users do not always provide location information in a structured format.

For example, a user may ask:

* "What's the weather in Dubai?"
* "How is the weather in London right now?"
* "Tell me the current weather in Chennai."
* "Is it raining in New York?"
* "What's the temperature in Singapore?"

The system should understand the user's natural-language request and determine the location from the prompt.

The workflow should then retrieve current weather information for that location.

---

## 3. Objective

Create a **single AI-agent workflow in n8n** that:

1. Accepts a natural-language user prompt.
2. Identifies the location mentioned in the prompt.
3. Determines whether the request is asking for current weather.
4. Calls a weather API using the identified location.
5. Retrieves the current weather information.
6. Generates a natural-language response.
7. Returns the response to the user.

---

## 4. Example

### User Input

```text
What is the weather like in Dubai right now?
```

### AI Agent Processing

```text
User Prompt
     ↓
AI Agent
     ↓
Extract Location
     ↓
Dubai
     ↓
Weather API
     ↓
Current Weather Data
     ↓
AI Agent
     ↓
Natural Language Response
```

### Expected Response

```text
The current weather in Dubai is 34°C with clear skies.
```

The exact weather values must come from the weather API and must not be invented by the AI agent.

---

## 5. Functional Requirements

### FR-01 — User Input

The workflow must accept a free-form natural-language prompt.

Example:

```text
What is the current weather in Chennai?
```

---

### FR-02 — Location Extraction

The AI agent must identify the location from the user's prompt.

Examples:

| User Prompt                 | Extracted Location |
| --------------------------- | ------------------ |
| Weather in Dubai            | Dubai              |
| Weather in London           | London             |
| Temperature in Chennai      | Chennai            |
| Is it raining in Singapore? | Singapore          |

---

### FR-03 — Weather Retrieval

The workflow must use a weather API to retrieve current weather information.

Possible information includes:

* Temperature
* Feels-like temperature
* Weather condition
* Humidity
* Wind speed
* Precipitation/rain
* Visibility
* Local date/time

Only information returned by the weather service should be presented as factual weather information.

---

### FR-04 — Natural Language Response

The AI agent should convert the API response into a concise and user-friendly response.

Example:

```text
The current weather in London is 18°C with light rain.
Humidity is 78% and the wind speed is 12 km/h.
```

---

### FR-05 — Missing Location

If the user does not provide a location, the agent should ask for one.

Example:

```text
What location would you like me to check the weather for?
```

---

### FR-06 — Invalid Location

If the location cannot be resolved, the workflow should provide a clear response.

Example:

```text
I couldn't find a location matching "XYZ123".
Could you provide a city or location name?
```

---

### FR-07 — Unsupported Request

If the user asks something unrelated to weather, the agent should respond appropriately.

Example:

```text
I can help you check the current weather for a location.
Please provide a city or location.
```

---

## 6. AI Agent Responsibilities

The AI agent should be responsible for:

* Understanding the user's natural-language request
* Identifying the location
* Determining the user's intent
* Calling the appropriate weather tool
* Interpreting the weather API response
* Generating the final conversational response

The AI agent should **not fabricate weather information**.

---

## 7. Weather Tool

Expose the weather API to the AI agent as a tool.

Conceptually:

```text
get_current_weather(location)
```

Input:

```json
{
  "location": "Dubai"
}
```

Output:

```json
{
  "location": "Dubai",
  "temperature": 34,
  "condition": "Clear",
  "humidity": 45,
  "windSpeed": 15
}
```

The actual schema should depend on the selected weather API.

---

## 8. Recommended n8n Workflow

The workflow can follow this structure:

```text
┌───────────────────┐
│   User Request    │
└─────────┬─────────┘
          ↓
┌───────────────────┐
│   n8n Trigger     │
└─────────┬─────────┘
          ↓
┌───────────────────┐
│     AI Agent      │
│                   │
│ Understand Prompt │
│ Extract Location  │
└─────────┬─────────┘
          ↓
┌───────────────────┐
│  Weather Tool     │
│                   │
│ Weather API       │
└─────────┬─────────┘
          ↓
┌───────────────────┐
│     AI Agent      │
│                   │
│ Format Response   │
└─────────┬─────────┘
          ↓
┌───────────────────┐
│   User Response   │
└───────────────────┘
```

---

## 9. Single-Agent Requirement

The solution should use **one AI agent** as the central reasoning component.

Avoid unnecessarily creating multiple agents such as:

```text
Location Agent
     ↓
Weather Agent
     ↓
Response Agent
```

Instead use:

```text
              ┌───────────────┐
User ────────►│   AI Agent    │
              └───────┬───────┘
                      │
                      ▼
                Weather Tool
                      │
                      ▼
                Weather API
```

The weather API should be treated as a **tool used by the agent**, not as another AI agent.

---

## 10. Error Handling

The workflow should gracefully handle:

### No location

```text
Please provide the city or location for which you want the weather.
```

### Invalid location

```text
I couldn't identify that location. Please provide a valid city or location.
```

### Weather API failure

```text
I'm unable to retrieve the current weather right now. Please try again later.
```

### API timeout

The workflow should handle timeout/failure without exposing technical details to the user.

---

## 11. Grounding Requirement

Weather information must always be grounded in the external weather API response.

The AI agent must not generate values such as:

```text
Temperature: 35°C
Humidity: 60%
```

unless those values were returned by the weather service.

The architecture should therefore be:

```text
Weather API
     ↓
Actual Weather Data
     ↓
AI Agent
     ↓
Natural Language
```

and not:

```text
User
     ↓
LLM Guess
     ↓
Weather Response
```

---

## 12. Example Test Cases

### Test Case 1 — City

Input:

```text
What's the weather in Dubai?
```

Expected:

```text
Location = Dubai
Weather API called
Current weather returned
```

---

### Test Case 2 — Natural Language

Input:

```text
Can you tell me how the weather is in London right now?
```

Expected:

```text
Location = London
```

---

### Test Case 3 — Missing Location

Input:

```text
What's the weather right now?
```

Expected:

```text
Ask user for location.
```

---

### Test Case 4 — Invalid Location

Input:

```text
What's the weather in XYZABC123?
```

Expected:

```text
Location cannot be resolved.
Ask user for a valid location.
```

---

### Test Case 5 — Follow-up

Input:

```text
What's the weather in Dubai?
```

Follow-up:

```text
What about tomorrow?
```

If the challenge only requires **current weather**, the agent should clearly indicate that the workflow supports current weather only, rather than silently providing a forecast.

---

## 13. Non-Functional Requirements

### Reliability

The workflow should handle weather API failures gracefully.

### Accuracy

Weather values must come from the weather API.

### Security

API keys must not be hard-coded in the workflow.

Use:

* n8n credentials
* Environment variables
* Secret management

### Maintainability

Keep:

* AI prompt
* Weather API configuration
* Credentials
* Tool configuration

separate where possible.

### Observability

The workflow should make it possible to identify:

* User request
* Extracted location
* Weather API call
* API success/failure
* Final response

---

## 14. Success Criteria

The solution is considered successful when:

* A user can provide a natural-language weather request.
* The AI agent correctly identifies the requested location.
* The agent calls the weather API.
* The workflow retrieves current weather information.
* The final response is grounded in the API response.
* Missing/invalid locations are handled gracefully.
* Weather API failures are handled gracefully.
* The workflow uses a single AI agent.
* No weather information is fabricated.

---

## 15. Key Design Principle

The project demonstrates the following AI-agent pattern:

```text
Natural Language
       ↓
AI Agent
       ↓
Understand Intent
       ↓
Extract Parameters
       ↓
Select Tool
       ↓
External API
       ↓
Structured Result
       ↓
AI Agent
       ↓
Natural Language Response
```

The core objective is to demonstrate a **single AI agent with tool usage**, rather than simply building a chatbot.

# END OF PROBLEM STATEMENT
