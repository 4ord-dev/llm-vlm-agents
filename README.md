# My Agent Project

Student: Nikita Breslavskyi

Student project for **Designing LLM/VLM Agents**.

## Setup

Create your own repository with **Use this template**, then clone your new
repository:

```bash
git clone <your-repository-url>
cd <your-repository-directory>
uv sync --locked
cp .env.example .env
uv run pytest
```

Add the individual OpenRouter key supplied by the instructor to `.env`. Never
commit this file or place the key in code, traces, issues, or reports.

## Coding Agent

If you already use Codex or Claude Code, nothing else is required. Otherwise,
install [Antigravity CLI](https://antigravity.google/docs/cli/install/) before
Meeting 1.

## Project Brief

- **Project title:** Personal desk assistant
- **Intended user:** The owner of this machine — a developer who wants one local agent that can see, read, speak, run commands, and use private stores on this computer.
- **Problem and primary task:** Take a goal from the owner and finish it on this machine: inspect allowed stores, read files, look at images, run scoped shell work, and use voice in and out when those tools are attached. The core is one loop: goal → choose a tool → observe → next step or a cited answer. The first working skill is: one question, one local image, and files the owner has mounted into the agent's store.
- **Why an agent is appropriate:** The job is multi-step and tool-shaped. The model does not already have the disk, the photo, or the command output. It has to decide what to open, what to run, and when it has enough to answer. That is an agent, not a chatbot.
- **Planned data:** Material the owner mounts into the agent: notes, documents, images, video, inventories, credentials, and identifiers. The owner picks host directories (absolute paths). Each one is a virtual mount the model sees, Linux-style: `D:/Projects/foo/agent-installation/data` → `/data`. The model only names virtual paths (`/data/...`, `/projects/...`). Tools resolve them to the mapped host path. Unmapped paths do not exist for file or shell tools. A default mount can be this repo's `data/` folder as `/data`; that is a mapping, not the whole disk.
- **Planned tools:** `list_store`, `search_store`, `read_file`, a structured image-facts tool, scoped shell on mounted paths, and voice I/O. Same tool names, different backends. File and shell arguments are virtual paths only. `tool_choice` stays `"auto"`; structured tools use Pydantic schemas.
- **Planned visual input:** Local images (and video frames when a clip is in the store) via `image_part`. The image-facts tool returns a short typed list the loop can act on.
- **Success criteria:** On a fixed set of owner-written cases, the agent answers the goal, uses tools instead of guessing, and cites virtual store paths or image fields it used. A case fails if a tool resolves or executes outside a mount, or if the answer cannot be checked against the store.
- **Non-goals and safety boundaries:** This is a personal machine agent, not a public service and not a jailbreak box. File and shell tools accept only virtual paths and stay inside their host mounts. Traces and answers use virtual paths, not raw home directories. Voice, keys, and personal data live in local env and mounted stores; they are not committed to the public git remote. The model API is the only required network call. No unsolicited scanning of the whole disk.

## Code

- `src/agent_project/llm.py` — OpenRouter client and mock client. A live call
  returns the text, tool calls, finish reason, model, provider, latency, and
  token usage with cost. Requests time out after 60 seconds and replies are
  limited to 1,024 tokens. If a provider returns an empty reply instead of the
  model's answer, the client retries once on another provider.
  `image_part(path)` adds an image to a message.
- `src/agent_project/agent.py` — the bounded tool loop.
- `src/agent_project/mounts.py` — virtual path resolution onto host mounts.
- `src/agent_project/tools.py` — tool schemas and dispatch.
- `src/agent_project/tracing.py` — a JSON Lines trace helper.
- `data/` — sample assistant store: `inbox.md`, `agenda.json`,
  `preferences.txt`, `projects.md`, `screen.png`.
- `traces/` — generated traces, ignored by Git.
- `evidence/` — the traces and results you submit.

## Running the agent

```bash
uv run python -m agent_project "What is on my agenda tonight?"
uv run python -m agent_project "What is on the captured screen?" --image /data/screen.png
uv run python -m agent_project "Where is the printer?"
```

The first command uses `list_store`, `search_store`, and `read_file` on `/data`.
The second attaches `data/screen.png` so the model can call `inspect_image`
and `image_facts`. A run stops on an answer, after 12 model steps, at USD 0.10, if the
same tool call repeats three times, or if the model returns an empty reply.
Traces go to `traces/agent.jsonl` and use virtual paths only.

## Tools

- `list_store` — list a virtual path such as `/data`
- `search_store` — match a query against names and text
- `read_file` — read a text file by virtual path
- `inspect_image` — load a mounted image for the next step
- `image_facts` — record a short typed list of facts from that image

File and image arguments are virtual paths only. Host paths and `..` are
rejected. The default mount is this repository's `data/` folder as `/data`.

## Course Limits

- One model for all live work: `google/gemma-4-26b-a4b-it`.
- USD 2 per key for the whole course, enforced by OpenRouter.
- In your own code: at most 12 model steps and USD 0.10 per agent run.

## Working with the Course Model

- The model usually requests one tool call per turn. Tell it in the system
  prompt that independent calls may be requested together.
- For typed output, such as a plan or facts read from an image, offer one tool
  whose parameters are your Pydantic schema and validate its arguments. Keep
  `tool_choice` at its default, `"auto"`, and give lists a maximum length;
  free-form JSON output sometimes repeats itself until the token limit.
- Results vary between identical runs. Run your fixed evaluation set at least
  three times and report the worst run as well as the average.
- A typical agent run costs well under USD 0.01. Use the mock client in tests.
- Copy the traces you submit to `evidence/`. Check them first for keys,
  personal data, and absolute file paths.

## Commands

```bash
uv run pytest
uv run ruff check .
uv run python -m agent_project "What is on my agenda tonight?"
```

Use the assignments published on the course website as the source of truth.
