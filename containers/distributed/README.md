# Distributed Splunk Lab

A personal lab for learning Splunk Enterprise data administration. It is not
meant for production use.

It runs a small distributed deployment in Docker Compose: a deployment server,
an indexer, a search head, a heavy forwarder, a universal forwarder, and some
log generators. Use it to practise data onboarding, deployment apps, parsing,
routing, and ingest actions.

It also has an lldap directory that sh1 uses for LDAP logins, and a private CA
for encrypting Splunk traffic. So far only uf1 -> hf1 forwarding uses SSL. The
cert steps and rollout plan are in [certs/README.md](certs/README.md).
