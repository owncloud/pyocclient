Changelog
=========

0.6
---

- Added support to query arbitrary properties with file info and file listing [NikosChondros]
- Added support for file operations within a public link [mrwunderbar666]

0.5
---

- Added "name" attribute for public links [PVince81]
- Fixed deprecation warnings [Tilman Lüttje] [PVince81]
- Added support sharing with federated users [remjg]
- Fixed setup script for utf-8 paths [amicitas]
- Fixed file mtime parsing issue [viraj96]
- Add support for the server's DAV v2 endpoint [PVince81]
- Remove support for ownCloud 8.1, 9.0 and 9.1 which are EOL [PVince81]

0.4
---

- Some code cleanup removing needless if statements [jamescooke]
- Remove old session_mode [PVince81]
- Set Depth to 0 in file_info call [PVince81]
- Make subclassing of Client event easier with protected methods [bobatsar]

0.3
---

- Make subclassing of Client easier [bobatsar]
- Add Depth param for recursive listing [bobatsar]
- Add shared_with_me parameter to get_shares [bobatsar]
- Link variable is now called url inside of shareinfo [SergioBertolinSG]
- Python3 support [ethifus] [Blizzz]

0.2
---

- Webdav COPY support [individual-it]
- Added API for federated sharing [nickvergessen]
- Fix login issue in case of failed login [individual-it]
- Added function to get capabilities [SergioBertolinSG]
- Added subadmin APIs for provisioning API [svigneux]
- Tests for provisioning API [individual-it]
- Added provisioning API functions [jennifer]
- Code cleanup / PEP8 formatting [jennifer]
- Added status check function [soalhn]
- Added share API functions [soalhn] [SergioBertolinSG]
- Travis integration [Gomez]
- Added session handling workaround for OC 5 [PVince81]
- Fixed many issues related to unicode path names [PVince81]
- Client now works properly on Windows [PVince81]

0.1
---

- Make python egg [PVince81]
- Initial release [PVince81]
