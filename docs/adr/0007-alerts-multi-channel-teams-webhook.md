# Alerts are multi-channel; Teams via incoming webhook

Issue #181 asks that build alerts — starting with a newly-opened `pipeline_failure` Build Incident,
and potentially the existing regression/recovery/overrun/ops alerts too — also reach a **Microsoft
Teams channel**, not just SMTP email. Email was the tool's only push channel, wired as a concrete
`EmailSender` that each `build_*` composer targeted directly by returning an email-shaped
`EmailMessage(subject, body, recipients)`. Adding Teams as a second peer channel forced a choice
about where the channel-vs-content boundary sits.

We decided to **generalize delivery into a multi-channel Alert layer**. Every `build_*` composer now
returns a **channel-neutral `Alert`** (title, summary lines, deep-link, severity, and its **kind**);
a post-commit **dispatcher** hands each `Alert` to every enabled **Alert Channel** whose subscription
includes that kind, and each channel renders it its own way. Two channels implement the
`AlertChannel` seam: `EmailAlertChannel` (the existing `SmtpEmailSender`, plain text as before) and
`TeamsAlertChannel` (POSTs an **Adaptive Card** to a single configured **incoming-webhook URL**).
Routing is a **full per-event × per-channel matrix**, expressed as two per-channel allowlists
(`EMAIL_EVENTS`, `TEAMS_EVENTS`) of Alert Kinds; the pre-existing `EMAIL_RECOVERY_NOTICE` flag is
**retired**, its effect subsumed by whether `recovery` is listed in `EMAIL_EVENTS`.

## Considered options

- **Transport: incoming webhook vs Microsoft Graph API.** Chose the **webhook URL** — a single
  secret POST target, flag-gated exactly like SMTP, with no OAuth, app registration, or
  admin-consented permissions. It works for both the legacy Office 365 connector and the newer Power
  Automate Workflows trigger (we target the Workflows `attachments` Adaptive-Card envelope, since the
  classic connector is being retired). Rejected **Graph API**: it needs an Azure AD app and
  client-credentials OAuth with `ChannelMessage.Send`, warranted only to post as a user identity or
  read replies — neither of which this ticket needs.

- **Abstraction: channel-neutral `Alert` vs shared-text wrapper vs parallel `TeamsSender`.** Chose
  **channel-neutral `Alert` (one compose, many renderers)**. Rejected **reusing the composed email
  text** and merely wrapping it for Teams: it would make Teams messages read like emails and forfeit
  card formatting (the `Action.OpenUrl` button). Rejected a **parallel `TeamsSender` with its own
  `build_*_teams` composers called alongside email at every site**: it duplicates every composer and
  scatters channel logic across call sites. The channel-neutral value keeps composition single and
  pushes rendering to the edge — at the cost of a one-time refactor of every composer and call site.

- **Routing: full matrix vs mirror vs strict-coupling.** Chose a **full per-event × per-channel
  matrix** so any kind can go to either channel independently. Rejected **Teams strictly mirrors
  email** (couples the two — you could not run Teams without SMTP) and **Teams mirrors email's event
  set with no independent control** (less surprising but gives up the control the operator asked for).

- **Matrix representation: per-channel allowlists vs ten booleans.** Chose **two comma-separated
  allowlists** (`EMAIL_EVENTS`, `TEAMS_EVENTS`), validated against the five known kinds at startup
  (fail-fast, like the `SMTP_STARTTLS` validator). Rejected **one boolean per cell**
  (`EMAIL_NOTIFY_INCIDENT`, `TEAMS_NOTIFY_REGRESSION`, …): ten keys to build, default, and document
  for the same expressiveness two allowlists give.

- **Retire `EMAIL_RECOVERY_NOTICE` vs keep it beside the allowlists.** Chose to **retire** it so both
  channels are configured by one symmetric mechanism. Rejected keeping it: email would then mix an
  ad-hoc boolean with an allowlist while Teams used only the allowlist — two idioms for one concept,
  harder to explain. The cost is one documented setting migration.

## Consequences

- **The dispatcher is the single filter point.** Per-kind routing lives in the dispatcher (send an
  `Alert` to a channel iff `alert.kind ∈ channel`'s allowlist), not scattered at call sites. Call
  sites compose the `Alert` once — and only when *some* enabled channel subscribes to that kind, so a
  fully-unsubscribed kind pays no composition cost (the classification/episode queries are skipped).
- **`clients.py` gains `build_channels(settings)`** returning the enabled channels, shared by the
  ingest pipeline and the poller — the same "no credential ⇒ skip that channel" rule email already
  follows (`TEAMS_WEBHOOK_URL` unset ⇒ no Teams channel; empty `*_EVENTS` ⇒ a configured channel that
  subscribes to nothing).
- **Delivery stays best-effort and post-commit.** Composed inside the ingest transaction (it needs
  the session), dispatched after the commit; each channel's send is independently wrapped so a
  webhook outage or an SMTP outage can neither fail nor roll back an ingest, nor block the other
  channel. `TeamsAlertChannel` uses the already-present `httpx` with a short timeout, mirroring the
  SMTP dial's fail-fast contract.
- **The offline gate is untouched.** `AlertChannel` is a Protocol; the suite drives fakes and opens
  no socket — the same seam discipline `EmailSender` established.
- **`TEAMS_WEBHOOK_URL` is a secret** (the URL embeds an auth token) — held for the POST only and
  never logged, exactly like `SMTP_PASSWORD`.
- **No dashboard footprint and no demo-dataset change** — alerting is a backend delivery concern with
  no user-visible surface, as SMTP email already is; the public Render demo simply leaves the Teams
  channel unconfigured.
- **`AlertKind.recovery`** is now the switch for recovery notices on *either* channel; the removed
  `EMAIL_RECOVERY_NOTICE` key is a breaking config change for any deployment that set it, documented
  in the README/`.env.example` sync.
