# Hackergram — An Open-Source Platform for Classical and LLM-Driven Web Security Experimentation

Hackergram is a deliberately vulnerable social-networking application, released fully open source so every
part of it can be read and inspected. It is built for both classical web-security experiments (SQL
injection, XSS, CSRF, and more) and attacks that involve LLM integration, such as prompt injection and
LLM-mediated SQL injection. It can be deployed locally, packaged as Docker containers, or run inside a full
GNS3 network topology for reproducible, isolated experimentation.

**Companion website (setup guides and all experiments):** <https://netexperiments.github.io/websecurity/>

> **Warning:** Hackergram is intentionally vulnerable. Run it only on your own machine or an isolated
> network, and never expose it to the Internet. It is intended for educational and research purposes only.
> See [Safety and Ethical Use](https://netexperiments.github.io/websecurity/safety/).

## Features

- **Posts:** create, edit, and delete posts shown to all users on the homepage
- **Friends:** send, accept, or decline friendship requests, and remove friendships
- **Profiles:** view any user's name, username, picture, bio, posts, and friends
- **Settings:** update your own name, password, picture, and bio
- **Search:** search posts by content or users by username
- **Messages:** exchange direct messages with other users
- **AI features:** AI-assisted post generation, post summarization, and a natural-language leaderboard,
  powered by locally hosted LLMs served through Ollama
- **Reset:** the `/reset` endpoint restores the application to its initial state at any time

## Covered experiments

Each experiment is documented step by step on the companion website, with the vulnerable code to inspect and
a countermeasure to implement:

- **Parser-driven injections:** SQL injection, NoSQL injection, XXE injection
- **Interpreter-driven injections:** cross-site scripting (stored, reflected, XSS worm), LLM-mediated SQL
  injection, LLM-mediated stored XSS, indirect prompt injection, system prompt leakage
- **Access and resource control:** path traversal
- **Request and interaction forgery:** CSRF, clickjacking, SSRF

## Architecture

Hackergram is a Python/Flask application with Jinja2 templates and a Bootstrap frontend. It stores its data
in MySQL (users, posts, friendships, leaderboard) and MongoDB (LLM chat history, direct messages), and calls
a local Ollama server for its AI features. See the
[Architecture](https://netexperiments.github.io/websecurity/architecture/) page for details.

| File / directory | Role |
|---|---|
| `hackergram.py` | Flask application entry point; configures the app and its databases |
| `views.py` | All routes: reads request data, calls `models.py` and Ollama, renders templates |
| `models.py` | Data-access layer for MySQL and MongoDB |
| `templates/` | Jinja2 templates |
| `static/` | CSS, JavaScript, and profile pictures |
| `start.sql` | MySQL schema and seed data (default users, posts, friendships) |
| `container_start.sh` | Container start script: starts MySQL and MongoDB, loads `start.sql`, starts Ollama, launches the app |
| `requirements.txt` | Python dependencies |

## Deployment options

| Deployment | Docker image(s) | Classical attacks | LLM attacks | GNS3 | Recommended use |
|---|---|---|---|---|---|
| Simple | `pimz23/hackergram-simple:latest` | Yes | No | No | Fastest introduction |
| Full | `pimz23/hackergram30:latest` | Yes | Yes | No | Complete single-host experimentation |
| GNS3 | `pimz23/hackergram30:latest`, `pimz23/my-gns3-attacker:1.5`, `pimz23/zap-desktop-novnc:latest`, `gns3/webterm:latest` | Yes | Yes | Yes | Networked experiments |

The simple image has no Ollama and none of the LLM endpoints. The full image (about 8.8 GB compressed)
includes Ollama and both LLM models.

## Quick start (Docker)

Requires Docker (tested with Docker Desktop 4.63.0, Docker Engine 29.2.1). Python is not needed: everything
runs inside the container.

1. Pull an image (simple shown here; use `pimz23/hackergram30:latest` for the full version):

   ```bash
   docker pull pimz23/hackergram-simple:latest
   ```

2. Start Hackergram:

   ```bash
   docker run -d --name hackergram -p 80:80 pimz23/hackergram-simple:latest
   ```

   The web application listens on port 80. If port 80 is taken, use `-p 8080:80` and open
   `http://localhost:8080/` instead.

3. Open <http://localhost:8080//> and log in as `mr_robot` / `elliot123`. The full list of default users is on
   the [Hackergram Overview](https://netexperiments.github.io/websecurity/labs/hackergram/) page.

4. To restore the initial state at any time, open <http://localhost/reset>.

5. Stop and remove the container:

   ```bash
   docker stop hackergram
   docker rm hackergram
   ```

The full step-by-step guide is on the [Quick Start](https://netexperiments.github.io/websecurity/quickstart/)
page. The GNS3 deployment, including the topology automation script, is described on the
[Lab Setup](https://netexperiments.github.io/websecurity/labs/attacks/lab-setup/) page.

## LLM configuration

Served by Ollama 0.17.7 through `POST http://localhost:11434/api/generate`. Each endpoint names its model
directly in `views.py`:

| Endpoint | Model | Inference options |
|---|---|---|
| `/leaderboard` | `llama2` (Llama 2, 7B) | temperature `0.1`, seed `42` |
| `/generate_post` | `mistral` (Mistral, 7B) | Ollama defaults |
| `/ai_summarize` | `mistral` (Mistral, 7B) | temperature `0.4`, seed `123` |

When running outside the full Docker image, pull both models first:

```bash
ollama pull llama2
ollama pull mistral
```

## Tested environment

| Component | Version |
|---|---|
| Operating system | Ubuntu 24.04.4 LTS (WSL 2 on Windows 11) |
| Python | 3.12.3 |
| Flask | 3.1.3 |
| MySQL | 8.0.46 |
| MongoDB | 8.0.19 |
| Docker | Docker Desktop 4.63.0 (Engine 29.2.1) |
| GNS3 | 2.2 |
| Ollama | 0.17.7 |
| LLM models | `llama2` (7B), `mistral` (7B) |

The Docker images are built on Ubuntu 20.04, so package versions inside the containers may differ.
See [Reproducibility](https://netexperiments.github.io/websecurity/reproducibility/) for image digests and
the full list of artifacts.

## Authors

- João Pimentel, Instituto Superior Técnico, Universidade de Lisboa
- Rui Valadas, Instituto Superior Técnico, Universidade de Lisboa
- Tiago Domingues, LastPass

## Citation

If you use Hackergram in your research, please cite it:

```bibtex
@software{hackergram2026,
  author  = {Pimentel, João and Valadas, Rui and Domingues, Tiago},
  title   = {Hackergram: An Open-Source Platform for Classical and LLM-Driven Web Security Experimentation},
  year    = {2026},
  version = {1.0},
  url     = {https://github.com/netexperiments/hackergramlab}
}
```

## Disclaimer

This lab is deliberately vulnerable and intended for educational and research purposes only. Do not use it in
production, and use the experiments only against your own Hackergram instance.
