# Security Findings Summary

**Last Updated**: 2025-10-31 16:37:55 UTC
**Total Active Findings**: 3
**Days Since Last Scan**: 0

**Severity Breakdown**:  
- **Medium**: 3  

## Current Findings

### Medium Severity

#### GHSA-4xh5-x5gv-qwph - ### Summary  In the fallback extraction path for source d...
- **Package**: pip 25.2
- **Source**: pip-audit
- **Discovered**: 2025-10-31 (0 days active)
- **Description**: ### Summary  In the fallback extraction path for source distributions, `pip` used Python’s `tarfile` module without verifying that symbolic/hard link targets resolve inside the intended extraction directory. A malicious sdist can include links that escape the target directory and overwrite arbitrary files on the invoking host during `pip install`.  ### Impact  Successful exploitation enables arbitrary file overwrite outside the build/extraction directory on the machine running `pip`. This can be...
- **Impact**: Vulnerability in pip package
- **Reference**: https://github.com/advisories/GHSA-4xh5-x5gv-qwph
- **Fix Available**: Yes (25.3)
- **Remediation**: Upgrade pip to version 25.3 when available
- **Planned Fix Date**: 2025-11-15
- **Assigned To**: dev-team
- **Workaround**: Avoid installing untrusted sdist packages

#### PYSEC-2022-42969 - The py library through 1
- **Package**: py 1.11.0
- **Source**: pip-audit
- **Discovered**: 2025-10-31 (0 days active)
- **Description**: The py library through 1.11.0 for Python allows remote attackers to conduct a ReDoS (Regular expression Denial of Service) attack via a Subversion repository with crafted info data, because the InfoSvnCommand argument is mishandled.
- **Impact**: Vulnerability in py package
- **Reference**: https://osv.dev/vulnerability/PYSEC-2022-42969
- **Fix Available**: No

#### PYSEC-2025-49 - setuptools is a package that allows users to download, bu...
- **Package**: setuptools 75.3.2
- **Source**: pip-audit
- **Discovered**: 2025-10-31 (0 days active)
- **Description**: setuptools is a package that allows users to download, build, install, upgrade, and uninstall Python packages. A path traversal vulnerability in `PackageIndex` is present in setuptools prior to version 78.1.1. An attacker would be allowed to write files to arbitrary locations on the filesystem with the permissions of the process running the Python code, which could escalate to remote code execution depending on the context. Version 78.1.1 fixes the issue.
- **Impact**: Vulnerability in setuptools package
- **Reference**: https://osv.dev/vulnerability/PYSEC-2025-49
- **Fix Available**: Yes (78.1.1)

## Remediation Summary

**Total Plans**: 1  
**Completed**: 1  

**Priority Breakdown**:  
**High**: 1  

