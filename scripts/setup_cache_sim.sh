#! /bin/bash

# Setup env variables to run the simulator

# bsolute path to this script
SCRIPT=$(readlink -f $0)
SCRIPT_PATH=$(dirname ${SCRIPT})
REPO_DIR=$(dirname ${SCRIPT_PATH})
ENV_FNAME="${SCRIPT_PATH}/cachestat.env"


function add-if-not-exist() {
	config_line=$1
	config_file=$2
	if ! sudo grep -qF "$config_line" "$config_file" ; then
		echo "$config_line" | sudo tee -a "$config_file"
	fi
}

echo "==> Repo directory: $REPO_DIR"
echo "==> Generate ${ENV_FNAME}"

touch -a $ENV_FNAME
add-if-not-exist "export CACHESTAT_ROOT_DIR=${REPO_DIR}" ${ENV_FNAME}

# Install libraries
pip3 install simpy
pip3 install numpy

# Make the directories
mkdir -p "${REPO_DIR}/simulator/results/"

# Add this into source
add-if-not-exist "source ${ENV_FNAME}"  ~/.bashrc
