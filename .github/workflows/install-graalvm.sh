#!/bin/bash
set -e -x

# Install GraalVM CE directly from GitHub releases (no SDKMAN).
# Usage: install-graalvm.sh <jdk-version>
# Example: install-graalvm.sh 23.0.1

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <jdk-version>"
  echo "  Example: $0 23.0.1"
  exit 1
fi

JDK_VERSION=$1
INSTALL_DIR="/opt/graalvm"

# System deps (Red Hat / manylinux)
yum install -y zip openssl-devel

# Download and install GraalVM CE
URL="https://github.com/graalvm/graalvm-ce-builds/releases/download/jdk-${JDK_VERSION}/graalvm-community-jdk-${JDK_VERSION}_linux-x64_bin.tar.gz"
echo "Downloading GraalVM CE JDK ${JDK_VERSION}"
curl -sfL "${URL}" -o /tmp/graalvm.tar.gz
mkdir -p "${INSTALL_DIR}"
tar xzf /tmp/graalvm.tar.gz -C "${INSTALL_DIR}" --strip-components=1
rm /tmp/graalvm.tar.gz

export JAVA_HOME="${INSTALL_DIR}"
export GRAALVM_HOME="${INSTALL_DIR}"
export PATH="${JAVA_HOME}/bin:${PATH}"

java --version
native-image --version
