# Security Policy

## Reporting a Vulnerability

Please report security issues privately through
[GitHub's private vulnerability reporting](https://github.com/OHF-voice/wyoming/security/advisories/new)
rather than opening a public issue.

Please include the affected version, a description of the issue, and the steps
needed to reproduce it. We aim to acknowledge reports within a week.

## Supported Versions

Fixes are released for the latest version only. Please upgrade before reporting.

## Security Model

**Wyoming is a peer-to-peer protocol for a trusted network. It has no
authentication, authorization, or transport encryption, by design.**

Anything that can reach a Wyoming service can use it. This is a property of the
protocol itself, not of any single implementation:

* Wyoming services do not authenticate their clients.
* Wyoming clients do not authenticate the services they connect to.
* Events are sent in the clear over TCP or a Unix socket.

Deploy Wyoming services on a network you control, and do not expose them
directly to the internet. If you need to cross an untrusted network, put the
connection inside something that provides authentication and encryption, such as
a VPN or an authenticating reverse proxy.

### HTTP servers

The optional HTTP servers (`wyoming.http.*`, installed with the `http` extra)
are gateways that translate HTTP requests into Wyoming events. They inherit the
security model above and add nothing of their own:

* **They are unauthenticated.** Any client that can reach one can use it.
* **They default to `--host 0.0.0.0`**, which listens on every interface. Pass
  `--host 127.0.0.1` to accept local connections only.
* **They run on the Flask development server**, which is not intended for
  production use or for exposure to untrusted clients.
* **`--allow-uri-override` lets any request choose the backend.** With this flag
  the server will connect wherever a request tells it to, which lets clients
  reach services they could not reach directly, and probe for services that are
  not running. Only enable it on a trusted network. Without it, requests are
  restricted to the service given by `--uri`.

Connections to backend services are bounded by `--connect-timeout` and
`--read-timeout` so that an unreachable or unresponsive service cannot occupy a
worker indefinitely.

## Scope

The following are working as intended and are not vulnerabilities on their own.
Please read the security model above before reporting them:

* A Wyoming service accepts events from any client that can connect to it.
* Wyoming traffic is not encrypted.
* An HTTP server serves any client that can reach it.
* An HTTP server started with `--allow-uri-override` connects to the address a
  request asks for.

Reports that assume Wyoming is meant to be safe when exposed to untrusted
clients are describing a deployment issue rather than a flaw in this project.
Findings that show a Wyoming service can be made to act outside the model above
are in scope and we want to hear about them.
