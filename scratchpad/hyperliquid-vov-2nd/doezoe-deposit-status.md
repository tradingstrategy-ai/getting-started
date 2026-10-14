# DOEZOE daily deposit status after leader-share recovery

This audit uses the pinned 7 October publication and the merged trading-strategy/executor readers. It calls both actual deposit-admission APIs at midnight UTC. Price rows count projected observations, not independent permission receipts. Open permission and a zero policy cap are separate facts; missing values remain NULL. Before 11 April the source applies its established assumed-open policy. The independent permission endpoint returned HTTP 404, so this report uses the published price projection.

## September transition

Original permission clocks determine age; publication and repeated price updates do not refresh them. A missing independent capacity clock does not remove a recorded share or explicit policy cap.

| Day (UTC) | Price rows | Permission | Admission | Reason | Leader share | Policy cap (USD) | Original permission time | Independent capacity time | Provenance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-09-13 | 19 | Open | Allowed | None | 0.8408558397099689 | NULL | 2026-09-12T20:14:30.257000000 | NULL | legacy_price_timestamp |
| 2026-09-14 | 19 | Open | Allowed | None | 0.8385510704694177 | NULL | 2026-09-13T22:27:33.550000000 | NULL | legacy_price_timestamp |
| 2026-09-15 | 19 | Open | Allowed | None | 0.8384149260115927 | NULL | 2026-09-14T20:19:08.668000000 | NULL | legacy_price_timestamp |
| 2026-09-16 | 17 | Open | Allowed | None | 0.8225604137308468 | NULL | 2026-09-15T23:05:35.330000000 | NULL | legacy_price_timestamp |
| 2026-09-17 | 21 | Open | Allowed | None | 0.8225604137308468 | NULL | 2026-09-16T20:03:32.433000000 | NULL | legacy_price_timestamp |
| 2026-09-18 | 22 | Open | Allowed | None | 0.8111075545043764 | NULL | 2026-09-17T20:17:20.807000000 | NULL | legacy_price_timestamp |
| 2026-09-19 | 25 | Open | Allowed | None | 0.8060933722302384 | NULL | 2026-09-18T22:00:33.173000000 | NULL | legacy_price_timestamp |
| 2026-09-20 | 22 | Open | Allowed | None | 0.7642291320444702 | NULL | 2026-09-19T19:18:42.377000000 | NULL | legacy_price_timestamp |
| 2026-09-21 | 25 | Open | Allowed | None | 0.7626572194187258 | NULL | 2026-09-20T18:51:40.208000000 | NULL | legacy_price_timestamp |
| 2026-09-22 | 23 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.6662941622202683 | NULL | 2026-09-21T21:05:07.848000000 | NULL | legacy_price_timestamp |
| 2026-09-23 | 20 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7342605277751546 | NULL | 2026-09-22T19:45:58.485000000 | NULL | legacy_price_timestamp |
| 2026-09-24 | 20 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7347530462540246 | NULL | 2026-09-23T20:33:14.272000000 | NULL | legacy_price_timestamp |
| 2026-09-25 | 19 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7391594219314553 | NULL | 2026-09-24T20:33:19.846000000 | NULL | legacy_price_timestamp |
| 2026-09-26 | 17 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.745999702228382 | NULL | 2026-09-25T21:40:18.242000000 | NULL | legacy_price_timestamp |

<details>
<summary>One row per day for all available 2026 dates</summary>

| Day (UTC) | Price rows | Permission | Admission | Reason | Leader share | Policy cap (USD) | Original permission time | Independent capacity time | Provenance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-01-01 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-02 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-03 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-04 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-05 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-06 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-07 | 2 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-08 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-09 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-10 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-11 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-12 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-13 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-14 | 2 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-15 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-16 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-17 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-18 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-19 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-20 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-21 | 2 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-22 | 0 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-23 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-24 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-25 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-26 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-27 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-28 | 2 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-29 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-30 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-01-31 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-01 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-02 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-03 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-04 | 2 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-05 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-06 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-07 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-08 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-09 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-10 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-11 | 2 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-12 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-13 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-14 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-15 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-16 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-17 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-18 | 2 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-19 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-20 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-21 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-22 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-23 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-24 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-25 | 2 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-26 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-27 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-02-28 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-03-01 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-03-02 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-03-03 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-03-04 | 2 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-03-05 | 1 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-03-06 | 1 | Open | Assumed open | None | NULL | NULL | 2026-03-06T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-07 | 1 | Open | Assumed open | None | NULL | NULL | 2026-03-07T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-08 | 1 | Open | Assumed open | None | NULL | NULL | 2026-03-08T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-09 | 1 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-09T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-10 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-10T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-11 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-11T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-12 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-12T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-13 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-13T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-14 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-14T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-15 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-15T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-16 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-16T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-17 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-17T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-18 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-18T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-19 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-19T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-20 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-20T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-21 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-21T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-22 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-22T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-23 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-23T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-24 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-24T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-25 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-25T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-26 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-26T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-27 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-27T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-28 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-28T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-29 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-29T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-30 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-30T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-03-31 | 2 | Open | Assumed open | None | 0.8515751914695803 | NULL | 2026-03-31T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-04-01 | 2 | Open | Assumed open | None | 0.8557674999512792 | NULL | 2026-04-01T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-04-02 | 2 | Open | Assumed open | None | 0.8557674999512792 | NULL | 2026-04-02T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-04-03 | 3 | Unknown | Assumed open | None | NULL | NULL | NULL | NULL | corrupted_unknown |
| 2026-04-04 | 9 | Open | Assumed open | None | 0.8557674999512792 | NULL | 2026-04-04T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-04-05 | 9 | Open | Assumed open | None | 0.8557674999512792 | NULL | 2026-04-05T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-04-06 | 9 | Open | Assumed open | None | 0.8557674999512792 | NULL | 2026-04-06T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-04-07 | 9 | Open | Assumed open | None | 0.8557674999512792 | NULL | 2026-04-07T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-04-08 | 9 | Open | Assumed open | None | 0.8557674999512792 | NULL | 2026-04-08T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-04-09 | 8 | Open | Assumed open | None | 0.8421607662784596 | NULL | 2026-04-09T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-04-10 | 14 | Open | Assumed open | None | 0.8421607662784596 | NULL | 2026-04-10T00:00:00.000000000 | NULL | legacy_price_timestamp |
| 2026-04-11 | 16 | Open | Allowed | None | 0.8421607662784596 | NULL | 2026-04-10T22:07:38.752000000 | NULL | legacy_price_timestamp |
| 2026-04-12 | 16 | Open | Allowed | None | 0.8421607662784596 | NULL | 2026-04-11T20:46:11.465000000 | NULL | legacy_price_timestamp |
| 2026-04-13 | 18 | Open | Allowed | None | 0.8421607662784596 | NULL | 2026-04-12T21:03:21.577000000 | NULL | legacy_price_timestamp |
| 2026-04-14 | 18 | Open | Allowed | None | 0.8557064287596597 | NULL | 2026-04-13T21:21:50.889000000 | NULL | legacy_price_timestamp |
| 2026-04-15 | 18 | Open | Allowed | None | 0.8113347994916256 | NULL | 2026-04-14T21:20:18.270000000 | NULL | legacy_price_timestamp |
| 2026-04-16 | 20 | Open | Allowed | None | 0.8103937628907175 | NULL | 2026-04-15T21:20:18.471000000 | NULL | legacy_price_timestamp |
| 2026-04-17 | 16 | Open | Allowed | None | 0.7941144060236316 | NULL | 2026-04-16T21:20:19.941000000 | NULL | legacy_price_timestamp |
| 2026-04-18 | 18 | Open | Allowed | None | 0.788167231664326 | NULL | 2026-04-17T21:20:26.571000000 | NULL | legacy_price_timestamp |
| 2026-04-19 | 18 | Open | Allowed | None | 0.789428026712733 | NULL | 2026-04-18T21:20:19.973000000 | NULL | legacy_price_timestamp |
| 2026-04-20 | 17 | Open | Allowed | None | 0.8120724076500762 | NULL | 2026-04-19T21:20:22.147000000 | NULL | legacy_price_timestamp |
| 2026-04-21 | 17 | Open | Allowed | None | 0.8120724076500762 | NULL | 2026-04-20T21:37:58.451000000 | NULL | legacy_price_timestamp |
| 2026-04-22 | 17 | Open | Allowed | None | 0.8120724076500762 | NULL | 2026-04-21T21:32:30.739000000 | NULL | legacy_price_timestamp |
| 2026-04-23 | 17 | Open | Allowed | None | 0.8120724076500762 | NULL | 2026-04-22T21:11:39.258000000 | NULL | legacy_price_timestamp |
| 2026-04-24 | 17 | Open | Allowed | None | 0.8120724076500762 | NULL | 2026-04-23T21:11:39.874000000 | NULL | legacy_price_timestamp |
| 2026-04-25 | 17 | Open | Allowed | None | 0.8117355859268849 | NULL | 2026-04-24T21:14:47.398000000 | NULL | legacy_price_timestamp |
| 2026-04-26 | 17 | Open | Allowed | None | 0.8120475561958207 | NULL | 2026-04-25T21:06:02.545000000 | NULL | legacy_price_timestamp |
| 2026-04-27 | 17 | Open | Allowed | None | 0.8120475561958207 | NULL | 2026-04-26T21:06:01.212000000 | NULL | legacy_price_timestamp |
| 2026-04-28 | 17 | Open | Allowed | None | 0.8120475561958207 | NULL | 2026-04-27T21:05:59.227000000 | NULL | legacy_price_timestamp |
| 2026-04-29 | 17 | Open | Allowed | None | 0.8120475561958207 | NULL | 2026-04-28T21:18:49.112000000 | NULL | legacy_price_timestamp |
| 2026-04-30 | 18 | Open | Allowed | None | 0.8120475561958207 | NULL | 2026-04-29T21:48:46.408000000 | NULL | legacy_price_timestamp |
| 2026-05-01 | 17 | Open | Allowed | None | 0.8120475561958207 | NULL | 2026-04-30T21:46:53.582000000 | NULL | legacy_price_timestamp |
| 2026-05-02 | 16 | Open | Allowed | None | 0.811406292435143 | NULL | 2026-05-01T21:24:28.288000000 | NULL | legacy_price_timestamp |
| 2026-05-03 | 18 | Open | Allowed | None | 0.8114639893703781 | NULL | 2026-05-02T21:24:52.046000000 | NULL | legacy_price_timestamp |
| 2026-05-04 | 18 | Open | Allowed | None | 0.8058447392426398 | NULL | 2026-05-03T21:25:54.105000000 | NULL | legacy_price_timestamp |
| 2026-05-05 | 22 | Open | Allowed | None | 0.800658232171521 | NULL | 2026-05-04T21:29:50.017000000 | NULL | legacy_price_timestamp |
| 2026-05-06 | 22 | Open | Allowed | None | 0.777934039225678 | NULL | 2026-05-05T21:34:24.490000000 | NULL | legacy_price_timestamp |
| 2026-05-07 | 19 | Open | Allowed | None | 0.7645937550984332 | NULL | 2026-05-06T21:42:15.566000000 | NULL | legacy_price_timestamp |
| 2026-05-08 | 18 | Open | Allowed | None | 0.7731479697529174 | NULL | 2026-05-07T21:42:12.330000000 | NULL | legacy_price_timestamp |
| 2026-05-09 | 16 | Open | Allowed | None | 0.7660905582606989 | NULL | 2026-05-08T21:58:51.244000000 | NULL | legacy_price_timestamp |
| 2026-05-10 | 18 | Open | Allowed | None | 0.781707692502645 | NULL | 2026-05-09T21:57:59.127000000 | NULL | legacy_price_timestamp |
| 2026-05-11 | 17 | Open | Allowed | None | 0.7964385940905125 | NULL | 2026-05-10T21:58:09.407000000 | NULL | legacy_price_timestamp |
| 2026-05-12 | 17 | Open | Allowed | None | 0.8041318499617309 | NULL | 2026-05-11T22:00:17.710000000 | NULL | legacy_price_timestamp |
| 2026-05-13 | 17 | Open | Allowed | None | 0.7946346657262703 | NULL | 2026-05-12T22:22:46.631000000 | NULL | legacy_price_timestamp |
| 2026-05-14 | 18 | Open | Allowed | None | 0.8038126762053472 | NULL | 2026-05-13T23:09:54.847000000 | NULL | legacy_price_timestamp |
| 2026-05-15 | 19 | Open | Allowed | None | 0.8206419520449217 | NULL | 2026-05-14T23:31:38.623000000 | NULL | legacy_price_timestamp |
| 2026-05-16 | 17 | Open | Allowed | None | 0.837813397682036 | NULL | 2026-05-15T23:36:02.834000000 | NULL | legacy_price_timestamp |
| 2026-05-17 | 17 | Open | Allowed | None | 0.837813397682036 | NULL | 2026-05-16T23:35:38.345000000 | NULL | legacy_price_timestamp |
| 2026-05-18 | 16 | Open | Allowed | None | 0.837813397682036 | NULL | 2026-05-17T23:36:04.124000000 | NULL | legacy_price_timestamp |
| 2026-05-19 | 18 | Open | Allowed | None | 0.8385088779974718 | NULL | 2026-05-18T20:21:13.326000000 | NULL | legacy_price_timestamp |
| 2026-05-20 | 18 | Open | Allowed | None | 0.8385088779974718 | NULL | 2026-05-19T20:18:24.415000000 | NULL | legacy_price_timestamp |
| 2026-05-21 | 16 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-20T20:26:00.942000000 | NULL | legacy_price_timestamp |
| 2026-05-22 | 17 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-21T20:43:03.039000000 | NULL | legacy_price_timestamp |
| 2026-05-23 | 18 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-22T20:43:04.493000000 | NULL | legacy_price_timestamp |
| 2026-05-24 | 16 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-23T21:02:20.719000000 | NULL | legacy_price_timestamp |
| 2026-05-25 | 17 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-24T21:04:04.337000000 | NULL | legacy_price_timestamp |
| 2026-05-26 | 14 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-25T21:03:45.668000000 | NULL | legacy_price_timestamp |
| 2026-05-27 | 13 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-26T09:05:32.505000000 | NULL | legacy_price_timestamp |
| 2026-05-28 | 17 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-27T22:37:49.628000000 | NULL | legacy_price_timestamp |
| 2026-05-29 | 16 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-28T23:42:04.616000000 | NULL | legacy_price_timestamp |
| 2026-05-30 | 15 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-29T22:16:46.220000000 | NULL | legacy_price_timestamp |
| 2026-05-31 | 16 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-30T18:50:47.983000000 | NULL | legacy_price_timestamp |
| 2026-06-01 | 16 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-05-31T20:51:17.013000000 | NULL | legacy_price_timestamp |
| 2026-06-02 | 15 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-01T23:18:14.909000000 | NULL | legacy_price_timestamp |
| 2026-06-03 | 15 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-02T20:29:03.804000000 | NULL | legacy_price_timestamp |
| 2026-06-04 | 16 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-03T22:43:07.227000000 | NULL | legacy_price_timestamp |
| 2026-06-05 | 16 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-04T23:09:45.269000000 | NULL | legacy_price_timestamp |
| 2026-06-06 | 17 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-05T21:11:28.331000000 | NULL | legacy_price_timestamp |
| 2026-06-07 | 17 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-06T21:01:20.146000000 | NULL | legacy_price_timestamp |
| 2026-06-08 | 17 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-07T21:01:20.374000000 | NULL | legacy_price_timestamp |
| 2026-06-09 | 17 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-08T22:03:13.242000000 | NULL | legacy_price_timestamp |
| 2026-06-10 | 16 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-09T21:48:06.921000000 | NULL | legacy_price_timestamp |
| 2026-06-11 | 15 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-10T22:14:32.833000000 | NULL | legacy_price_timestamp |
| 2026-06-12 | 13 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-11T14:41:11.048000000 | NULL | legacy_price_timestamp |
| 2026-06-13 | 15 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-12T22:13:10.715000000 | NULL | legacy_price_timestamp |
| 2026-06-14 | 15 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-13T17:41:08.936000000 | NULL | legacy_price_timestamp |
| 2026-06-15 | 16 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-14T17:10:07.358000000 | NULL | legacy_price_timestamp |
| 2026-06-16 | 17 | Open | Allowed | None | 0.8415648987036993 | NULL | 2026-06-15T21:16:07.831000000 | NULL | legacy_price_timestamp |
| 2026-06-17 | 17 | Open | Allowed | None | 0.8431886225459633 | NULL | 2026-06-16T21:17:05.475000000 | NULL | legacy_price_timestamp |
| 2026-06-18 | 16 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-17T21:24:07.188000000 | NULL | legacy_price_timestamp |
| 2026-06-19 | 13 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-18T21:33:07.285000000 | NULL | legacy_price_timestamp |
| 2026-06-20 | 15 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-19T17:38:08.780000000 | NULL | legacy_price_timestamp |
| 2026-06-21 | 16 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-20T21:51:05.325000000 | NULL | legacy_price_timestamp |
| 2026-06-22 | 18 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-21T21:50:43.736000000 | NULL | legacy_price_timestamp |
| 2026-06-23 | 14 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-22T21:54:09.409000000 | NULL | legacy_price_timestamp |
| 2026-06-24 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-23T22:03:45.048000000 | NULL | legacy_price_timestamp |
| 2026-06-25 | 14 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-24T22:04:07.050000000 | NULL | legacy_price_timestamp |
| 2026-06-26 | 15 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-25T22:28:07.579000000 | NULL | legacy_price_timestamp |
| 2026-06-27 | 15 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-26T23:06:07.252000000 | NULL | legacy_price_timestamp |
| 2026-06-28 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-27T23:06:09.869000000 | NULL | legacy_price_timestamp |
| 2026-06-29 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-28T22:43:36.577000000 | NULL | legacy_price_timestamp |
| 2026-06-30 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-29T22:45:23.927000000 | NULL | legacy_price_timestamp |
| 2026-07-01 | 13 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-06-30T22:26:37.357000000 | NULL | legacy_price_timestamp |
| 2026-07-02 | 15 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-01T18:29:05.567000000 | NULL | legacy_price_timestamp |
| 2026-07-03 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-02T22:39:02.427000000 | NULL | legacy_price_timestamp |
| 2026-07-04 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-03T23:16:00.543000000 | NULL | legacy_price_timestamp |
| 2026-07-05 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-04T23:05:01.981000000 | NULL | legacy_price_timestamp |
| 2026-07-06 | 16 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-05T23:30:00.585000000 | NULL | legacy_price_timestamp |
| 2026-07-07 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-06T21:02:18.152000000 | NULL | legacy_price_timestamp |
| 2026-07-08 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-07T21:02:17.685000000 | NULL | legacy_price_timestamp |
| 2026-07-09 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-08T21:40:14.328000000 | NULL | legacy_price_timestamp |
| 2026-07-10 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-09T21:52:13.491000000 | NULL | legacy_price_timestamp |
| 2026-07-11 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-10T22:44:21.414000000 | NULL | legacy_price_timestamp |
| 2026-07-12 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-11T23:14:07.470000000 | NULL | legacy_price_timestamp |
| 2026-07-13 | 18 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-12T23:09:07.803000000 | NULL | legacy_price_timestamp |
| 2026-07-14 | 25 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-13T23:38:45.288000000 | NULL | legacy_price_timestamp |
| 2026-07-15 | 25 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-14T23:42:54.120000000 | NULL | legacy_price_timestamp |
| 2026-07-16 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-15T22:21:40.567000000 | NULL | legacy_price_timestamp |
| 2026-07-17 | 18 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-16T22:07:05.122000000 | NULL | legacy_price_timestamp |
| 2026-07-18 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-17T20:04:08.313000000 | NULL | legacy_price_timestamp |
| 2026-07-19 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-18T21:28:05.440000000 | NULL | legacy_price_timestamp |
| 2026-07-20 | 17 | Open | Allowed | None | 0.8451243996910158 | NULL | 2026-07-19T22:38:42.500000000 | NULL | legacy_price_timestamp |
| 2026-07-21 | 17 | Open | Allowed | None | 0.779108644141785 | NULL | 2026-07-20T22:50:16.712000000 | NULL | legacy_price_timestamp |
| 2026-07-22 | 17 | Open | Allowed | None | 0.779108644141785 | NULL | 2026-07-21T23:39:53.700000000 | NULL | legacy_price_timestamp |
| 2026-07-23 | 17 | Open | Allowed | None | 0.779108644141785 | NULL | 2026-07-22T23:53:06.615000000 | NULL | legacy_price_timestamp |
| 2026-07-24 | 16 | Open | Allowed | None | 0.779108644141785 | NULL | 2026-07-23T23:52:47.370000000 | NULL | legacy_price_timestamp |
| 2026-07-25 | 15 | Open | Allowed | None | 0.779108644141785 | NULL | 2026-07-24T22:07:24.095000000 | NULL | legacy_price_timestamp |
| 2026-07-26 | 13 | Open | Allowed | None | 0.779108644141785 | NULL | 2026-07-25T14:35:45.607000000 | NULL | legacy_price_timestamp |
| 2026-07-27 | 16 | Open | Allowed | None | 0.779108644141785 | NULL | 2026-07-26T19:23:08.765000000 | NULL | legacy_price_timestamp |
| 2026-07-28 | 17 | Open | Allowed | None | 0.8451218334184653 | NULL | 2026-07-27T21:29:38.675000000 | NULL | legacy_price_timestamp |
| 2026-07-29 | 17 | Open | Allowed | None | 0.8451218334184653 | NULL | 2026-07-28T21:26:11.724000000 | NULL | legacy_price_timestamp |
| 2026-07-30 | 16 | Open | Allowed | None | 0.8451218334184653 | NULL | 2026-07-29T21:26:08.034000000 | NULL | legacy_price_timestamp |
| 2026-07-31 | 17 | Open | Allowed | None | 0.8451218334184653 | NULL | 2026-07-30T21:15:28.469000000 | NULL | legacy_price_timestamp |
| 2026-08-01 | 17 | Open | Allowed | None | 0.8451218334184653 | NULL | 2026-07-31T22:00:15.876000000 | NULL | legacy_price_timestamp |
| 2026-08-02 | 17 | Open | Allowed | None | 0.8451218334184653 | NULL | 2026-08-01T22:39:50.456000000 | NULL | legacy_price_timestamp |
| 2026-08-03 | 17 | Open | Allowed | None | 0.8451218334184653 | NULL | 2026-08-02T23:30:13.363000000 | NULL | legacy_price_timestamp |
| 2026-08-04 | 17 | Open | Allowed | None | 0.8451218334184653 | NULL | 2026-08-03T23:35:46.714000000 | NULL | legacy_price_timestamp |
| 2026-08-05 | 18 | Open | Allowed | None | 0.8451218334184653 | NULL | 2026-08-04T20:26:43.108000000 | NULL | legacy_price_timestamp |
| 2026-08-06 | 16 | Open | Allowed | None | 0.845129716899752 | NULL | 2026-08-05T21:11:31.783000000 | NULL | legacy_price_timestamp |
| 2026-08-07 | 17 | Open | Allowed | None | 0.845129716899752 | NULL | 2026-08-06T21:34:31.370000000 | NULL | legacy_price_timestamp |
| 2026-08-08 | 17 | Open | Allowed | None | 0.845129716899752 | NULL | 2026-08-07T21:34:31.362000000 | NULL | legacy_price_timestamp |
| 2026-08-09 | 17 | Open | Allowed | None | 0.845129716899752 | NULL | 2026-08-08T21:35:30.481000000 | NULL | legacy_price_timestamp |
| 2026-08-10 | 17 | Open | Allowed | None | 0.845129716899752 | NULL | 2026-08-09T22:06:50.904000000 | NULL | legacy_price_timestamp |
| 2026-08-11 | 17 | Open | Allowed | None | 0.845129716899752 | NULL | 2026-08-10T22:06:54.649000000 | NULL | legacy_price_timestamp |
| 2026-08-12 | 17 | Open | Allowed | None | 0.845129716899752 | NULL | 2026-08-11T22:06:51.165000000 | NULL | legacy_price_timestamp |
| 2026-08-13 | 17 | Open | Allowed | None | 0.845129716899752 | NULL | 2026-08-12T22:24:25.314000000 | NULL | legacy_price_timestamp |
| 2026-08-14 | 17 | Open | Allowed | None | 0.845129716899752 | NULL | 2026-08-13T22:24:28.422000000 | NULL | legacy_price_timestamp |
| 2026-08-15 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-14T22:31:25.772000000 | NULL | legacy_price_timestamp |
| 2026-08-16 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-15T22:30:08.664000000 | NULL | legacy_price_timestamp |
| 2026-08-17 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-16T22:30:09.139000000 | NULL | legacy_price_timestamp |
| 2026-08-18 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-17T23:13:08.229000000 | NULL | legacy_price_timestamp |
| 2026-08-19 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-18T23:12:34.073000000 | NULL | legacy_price_timestamp |
| 2026-08-20 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-19T23:15:49.949000000 | NULL | legacy_price_timestamp |
| 2026-08-21 | 16 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-20T23:14:11.716000000 | NULL | legacy_price_timestamp |
| 2026-08-22 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-21T20:02:51.482000000 | NULL | legacy_price_timestamp |
| 2026-08-23 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-22T20:02:27.403000000 | NULL | legacy_price_timestamp |
| 2026-08-24 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-23T20:03:03.042000000 | NULL | legacy_price_timestamp |
| 2026-08-25 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-24T22:15:27.079000000 | NULL | legacy_price_timestamp |
| 2026-08-26 | 17 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-25T22:28:26.670000000 | NULL | legacy_price_timestamp |
| 2026-08-27 | 18 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-26T22:41:02.382000000 | NULL | legacy_price_timestamp |
| 2026-08-28 | 20 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-27T23:16:48.503000000 | NULL | legacy_price_timestamp |
| 2026-08-29 | 16 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-28T23:39:42.121000000 | NULL | legacy_price_timestamp |
| 2026-08-30 | 19 | Open | Allowed | None | 0.8447781119888558 | NULL | 2026-08-29T20:13:07.565000000 | NULL | legacy_price_timestamp |
| 2026-08-31 | 21 | Open | Allowed | None | 0.8451819817866151 | NULL | 2026-08-30T21:05:33.383000000 | NULL | legacy_price_timestamp |
| 2026-09-01 | 18 | Open | Allowed | None | 0.8452135414925079 | NULL | 2026-08-31T21:39:22.060000000 | NULL | legacy_price_timestamp |
| 2026-09-02 | 17 | Open | Allowed | None | 0.8452135414925079 | NULL | 2026-09-01T21:38:32.328000000 | NULL | legacy_price_timestamp |
| 2026-09-03 | 17 | Open | Allowed | None | 0.8452135414925079 | NULL | 2026-09-02T15:49:28.018000000 | NULL | legacy_price_timestamp |
| 2026-09-04 | 23 | Open | Allowed | None | 0.8452135414925079 | NULL | 2026-09-03T20:46:56.941000000 | NULL | legacy_price_timestamp |
| 2026-09-05 | 15 | Open | Allowed | None | 0.8403197070522815 | NULL | 2026-09-04T20:16:24.466000000 | NULL | legacy_price_timestamp |
| 2026-09-06 | 20 | Open | Allowed | None | 0.8452461301090904 | NULL | 2026-09-05T19:44:22.081000000 | NULL | legacy_price_timestamp |
| 2026-09-07 | 17 | Open | Allowed | None | 0.8426403686032021 | NULL | 2026-09-06T23:39:30.967000000 | NULL | legacy_price_timestamp |
| 2026-09-08 | 17 | Open | Allowed | None | 0.8428021395765185 | NULL | 2026-09-07T23:11:49.658000000 | NULL | legacy_price_timestamp |
| 2026-09-09 | 17 | Open | Allowed | None | 0.8436035130544958 | NULL | 2026-09-08T22:07:14.421000000 | NULL | legacy_price_timestamp |
| 2026-09-10 | 21 | Open | Allowed | None | 0.8020416511748772 | NULL | 2026-09-09T21:34:53.829000000 | NULL | legacy_price_timestamp |
| 2026-09-11 | 19 | Open | Allowed | None | 0.8022664242789461 | NULL | 2026-09-10T20:33:48.430000000 | NULL | legacy_price_timestamp |
| 2026-09-12 | 16 | Open | Allowed | None | 0.8410655911118733 | NULL | 2026-09-11T22:28:15.940000000 | NULL | legacy_price_timestamp |
| 2026-09-13 | 19 | Open | Allowed | None | 0.8408558397099689 | NULL | 2026-09-12T20:14:30.257000000 | NULL | legacy_price_timestamp |
| 2026-09-14 | 19 | Open | Allowed | None | 0.8385510704694177 | NULL | 2026-09-13T22:27:33.550000000 | NULL | legacy_price_timestamp |
| 2026-09-15 | 19 | Open | Allowed | None | 0.8384149260115927 | NULL | 2026-09-14T20:19:08.668000000 | NULL | legacy_price_timestamp |
| 2026-09-16 | 17 | Open | Allowed | None | 0.8225604137308468 | NULL | 2026-09-15T23:05:35.330000000 | NULL | legacy_price_timestamp |
| 2026-09-17 | 21 | Open | Allowed | None | 0.8225604137308468 | NULL | 2026-09-16T20:03:32.433000000 | NULL | legacy_price_timestamp |
| 2026-09-18 | 22 | Open | Allowed | None | 0.8111075545043764 | NULL | 2026-09-17T20:17:20.807000000 | NULL | legacy_price_timestamp |
| 2026-09-19 | 25 | Open | Allowed | None | 0.8060933722302384 | NULL | 2026-09-18T22:00:33.173000000 | NULL | legacy_price_timestamp |
| 2026-09-20 | 22 | Open | Allowed | None | 0.7642291320444702 | NULL | 2026-09-19T19:18:42.377000000 | NULL | legacy_price_timestamp |
| 2026-09-21 | 25 | Open | Allowed | None | 0.7626572194187258 | NULL | 2026-09-20T18:51:40.208000000 | NULL | legacy_price_timestamp |
| 2026-09-22 | 23 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.6662941622202683 | NULL | 2026-09-21T21:05:07.848000000 | NULL | legacy_price_timestamp |
| 2026-09-23 | 20 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7342605277751546 | NULL | 2026-09-22T19:45:58.485000000 | NULL | legacy_price_timestamp |
| 2026-09-24 | 20 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7347530462540246 | NULL | 2026-09-23T20:33:14.272000000 | NULL | legacy_price_timestamp |
| 2026-09-25 | 19 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7391594219314553 | NULL | 2026-09-24T20:33:19.846000000 | NULL | legacy_price_timestamp |
| 2026-09-26 | 17 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.745999702228382 | NULL | 2026-09-25T21:40:18.242000000 | NULL | legacy_price_timestamp |
| 2026-09-27 | 18 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.746002656501675 | NULL | 2026-09-26T22:24:33.444000000 | NULL | legacy_price_timestamp |
| 2026-09-28 | 18 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7466919826776749 | NULL | 2026-09-27T22:24:44.517000000 | NULL | legacy_price_timestamp |
| 2026-09-29 | 19 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7473523509838044 | NULL | 2026-09-28T23:33:26.050000000 | NULL | legacy_price_timestamp |
| 2026-09-30 | 17 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7666729732394755 | NULL | 2026-09-29T23:45:51.361000000 | NULL | legacy_price_timestamp |
| 2026-10-01 | 17 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7666729732394755 | NULL | 2026-09-30T21:23:50.951000000 | NULL | legacy_price_timestamp |
| 2026-10-02 | 17 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7687839288920518 | NULL | 2026-10-01T20:10:59.586000000 | NULL | legacy_price_timestamp |
| 2026-10-03 | 17 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7690010999936446 | NULL | 2026-10-02T21:28:15.378000000 | NULL | legacy_price_timestamp |
| 2026-10-04 | 17 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7690010999936446 | NULL | 2026-10-03T21:47:19.486000000 | NULL | legacy_price_timestamp |
| 2026-10-05 | 13 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7854633358962072 | NULL | 2026-10-04T21:47:53.792000000 | NULL | legacy_price_timestamp |
| 2026-10-06 | 17 | Closed | Blocked | DepositBlockReason.vault_deposits_closed | 0.7854633358962072 | NULL | 2026-10-04T21:47:53.792000000 | NULL | legacy_price_timestamp |
| 2026-10-07 | 15 | Open | Blocked | DepositBlockReason.vault_max_deposit_zero | 0.049999999992533455 | 0.0 | 2026-10-06T20:47:02.098804000 | 2026-10-06T20:47:02.098804000 | observed |

</details>

[Backtest rerun and input hashes](restored-data-rerun-2026-10-07.md).
