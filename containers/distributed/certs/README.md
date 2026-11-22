# Splunk SSL with a private CA

Goal: replace Splunk's default certs (signed by the shared `SplunkCommonCA`) with
certs from our own CA, then turn on SSL for every Splunk hop.

Design decided:
- One private **root CA** (no intermediate), host certs signed directly by it.
- **One cert per host** (`idx1`, `hf1`, `sh1`, `ds1`, `uf1`), CN + SAN = Docker hostname.
- Host keys **unencrypted** (no `sslPassword` needed). Only `ca.key` has a passphrase.
- Certs generated centrally here, pushed via the DS in **per-host apps**
  (e.g. `deployment-apps/hf1_ssl/`), confs committed, cert files gitignored.
  ds1 gets its app via `make provision-ds` (it is not a deployment client).
- Don't reuse Caddy's root (`caddy-root.crt`): Caddy owns/rotates it, and wiping
  `caddy_data` would break web and Splunk at the same time.

## Progress

- [x] Step 1: `certs/` folder, already gitignored (`/containers/distributed/certs/*` in root `.gitignore`)
- [x] Step 2: CA created (`ca/ca.key`, `ca/ca.pem`, CN=splunk-lab-ca, valid to Nov 2036)
- [x] Step 3: hf1 key + CSR (`hf1/hf1.key`, `hf1/hf1.csr`)
- [x] Step 4: sign hf1's CSR (`hf1/hf1.crt`, valid to Feb 2029)
- [x] Step 5: verify hf1.crt (chain OK, CA:FALSE, DNS:hf1, key matches cert)
- [x] Step 6: build combined PEM for Splunk (`hf1/hf1.pem`: cert, key, CA)
- [x] Add `*.pem`, `*.key`, `*.csr` to root `.gitignore` (verified with `git check-ignore`)
- [x] Rollout stage 1: uf1 -> hf1:9998 over SSL working (2026-11-19, `ssl=true`, `cookedSSL`)
  - Apps: `hf1_ssl` (receiver + hf1.pem), `uf1_ssl` (`[tcpout] clientCert`), `all_ssl_trust`
    (server.conf sslRootCAPath, forwarder class only for now), `uf_outputs_to_hf` (useSSL, verify, altname)
  - Gotcha (10.4.2): `useSSL = true` without `clientCert` fails SSL context init with
    "Can't read ca certificate file <blank>" and **silently falls back to plaintext**.
    clientCert is effectively required even with `requireClientCert = false` on the receiver.
  - [x] Removed `sslRootCAPath` from outputs.conf; tcpout uses server.conf `[sslConfig] sslRootCAPath`
    from `all_ssl_trust` fine (2026-11-19). SSL settings live in `[tcpout]` of `uf_outputs_to_hf`.
  - [x] Negative test passed (2026-11-19): `sslAltNameToCheck = hf2` ->
    `ERROR X509 - X509 certificate (CN=hf1) alternate name (hf1) did not match any allowed names (,hf2)`,
    uf1 refused to connect. Verification is enforced (fails closed, unlike SSL context init).
  - [x] Reverted `sslAltNameToCheck` to `hf1`
  - [x] Moved SSL input to 9997 (`[splunktcp-ssl:9997]`), uf1 -> `hf1:9997`, `all_receiving` unmapped
    from heavy_forwarder (2026-11-19). hf1 logs "port 9997 is reserved for splunk 2 splunk (SSL)".
  - [x] Docker image provisioning (splunk-ansible `splunk.s2s`, default enable/9997/no SSL) wrote
    `[splunktcp://9997] disabled = 0` into `etc/system/local/inputs.conf` on EVERY node, on every start.
    Fixed 2026-11-19: `SPLUNK_S2S_PORT: "0"` in the compose `x-splunk-env` anchor (task only runs when
    port is non-zero), deleted the existing system/local inputs.conf on all 5 nodes, recreated containers.
    Do NOT use `s2s.enable: False`: it writes `disabled = 1` to system/local, which overrides
    `all_receiving` and would stop idx1 receiving. Receivers now come only from DS apps.

## Stage 1 done. Next: stage 2 (hf1/sh1 -> idx1) (**pick up here**)
- [ ] Rollout stages 2-4 (see bottom)

## Commands (run from `containers/distributed/`)

### Step 2: CA (done)
```bash
openssl genrsa -aes256 -out certs/ca/ca.key 4096
openssl req -x509 -new -key certs/ca/ca.key -sha256 -days 3650 \
  -subj "/CN=splunk-lab-ca" -out certs/ca/ca.pem
openssl x509 -in certs/ca/ca.pem -noout -subject -issuer -dates -ext basicConstraints
```

### Step 3: host key + CSR (done for hf1)
```bash
openssl genrsa -out certs/hf1/hf1.key 2048
openssl req -new -key certs/hf1/hf1.key -subj "/CN=hf1" -out certs/hf1/hf1.csr
openssl req -in certs/hf1/hf1.csr -noout -subject -verify
```

### Step 4: CA signs the CSR
```bash
cat > certs/hf1/hf1.ext <<'EOF'
basicConstraints=critical,CA:FALSE
subjectAltName=DNS:hf1
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth,clientAuth
EOF

openssl x509 -req -in certs/hf1/hf1.csr \
  -CA certs/ca/ca.pem -CAkey certs/ca/ca.key -CAcreateserial \
  -days 825 -sha256 -extfile certs/hf1/hf1.ext \
  -out certs/hf1/hf1.crt
```

### Step 5: verify
```bash
openssl verify -CAfile certs/ca/ca.pem certs/hf1/hf1.crt
openssl x509 -in certs/hf1/hf1.crt -noout -subject -issuer \
  -ext basicConstraints,subjectAltName,extendedKeyUsage
```
Expect: `OK`, issuer `CN=splunk-lab-ca`, `CA:FALSE`, `DNS:hf1`, serverAuth + clientAuth.

### Step 6: combined PEM (Splunk wants cert, key, CA in one file)
```bash
cat certs/hf1/hf1.crt certs/hf1/hf1.key certs/ca/ca.pem > certs/hf1/hf1.pem
```
Repeat steps 3-6 per host, swapping the name. Later: wrap in a `make certs` loop.

## Concepts (quick reference)

- **CA**: just a key pair + self-signed cert that machines are told to trust.
  Public CAs are trusted because their roots ship in OS/browsers; ours is trusted
  because we set `sslRootCAPath = ca.pem`.
- **Root vs intermediate**: an intermediate sits between root and hosts so the root
  key can stay offline. Not using one. If added, host PEMs need the full chain.
- **CSR**: a host's request for a cert = public key + requested name + signed with
  the host's private key (proves possession). Private key never leaves the host.
  Production pattern: host makes key + CSR, only CSR goes to the CA.
- **Cert fields**: version, serial, signature algorithm, issuer, validity, subject,
  public key, extensions, CA signature. CSR only carries subject + public key; CA
  adds the rest when signing.
- **CN** = Common Name, one field of the subject (others: C, ST, L, O, OU).
  Modern TLS checks **SAN** instead; Splunk has `sslCommonNameToCheck` (CN) and
  `sslAltNameToCheck` (SAN).
- **Basic Constraints** (an extension): `CA:TRUE` = may sign certs, `CA:FALSE` = may
  not. Stops a stolen host key (e.g. hf1's) from minting a fake cert for idx1.
- **critical** (a per-extension flag): software that doesn't understand the extension
  must reject the cert rather than ignore it.
- **keyUsage / extendedKeyUsage**: what the key is allowed to do. `serverAuth` =
  can be a TLS server, `clientAuth` = can be a TLS client (mutual auth).
- **ACME** (RFC 8555): protocol for automatic cert issuance/renewal (Let's Encrypt,
  Caddy). Splunk has no ACME client, so its certs are files referenced from conf.

## Current state of Splunk TLS (before this work)

- Splunk Web 8000: default `etc/auth/splunkweb/cert.pem` (Caddy proxies with `tls_insecure_skip_verify`)
- Mgmt 8089: default `etc/auth/server.pem`, `sslPassword` default `password`
- HEC on hf1: `enableSSL = 1`, default `server.pem`
- S2S 9997: plaintext
- Caddy browser-side TLS: `tls internal` (Caddy's own CA, root exported as `caddy-root.crt`)
- Unrelated: `SPLUNK_PASS4SYMMKEY` = shared secret for Splunk-to-Splunk auth
  (license, DS, clustering), changed from default `changeme`. Not a cert setting.

## Rollout stages

1. **uf1 -> hf1**: `hf1_ssl` app with `[splunktcp-ssl:9998]` + `[SSL] serverCert`;
   `uf_outputs_to_hf` -> `hf1:9998` + `sslRootCAPath` + `sslVerifyServerCert`.
   Verify: `index=_internal source=*metrics.log group=tcpin_connections` on hf1, `splunkd.log` for SSL errors.
   Run 9998 alongside 9997 until it works, then remove the plain input.
2. **hf1/sh1 -> idx1**: idx1 cert + `idx1_ssl` receiver, switch `all_outputs_to_idx`.
3. **Splunk Web, then HEC**: web.conf `serverCert` + `privKeyPath` (separate files),
   then Caddy `trusted_ca_certs` and drop `tls_insecure_skip_verify` per block.
4. **Mgmt port (8089) last**: ds1 first, then clients; enable verification only once
   everything is encrypted, or clients lose phone-home and need manual fixing.

Conf file layouts: `web.conf` takes cert and key as separate files; `server.conf`
`[sslConfig]`, `inputs.conf [SSL]`, `outputs.conf` take the combined PEM.
