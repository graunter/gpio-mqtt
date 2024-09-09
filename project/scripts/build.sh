#!/bin/bash

# TODO: #:, pyyaml (>= 6.0.1), paho-mqtt (>= 2.1.0)


BUILD_PLATFORM_ADDRESS=$1
BUILD_PLATFORM_PORT=$2
BUILD_PLATFORM_PASS=$3
BUILD_USER=$4

# Info: you need sshpass packet for this script:
# sudo apt-get install sshpass

cmd="dpkg --print-architecture"
ARCHITECTURE=$(sshpass -p $BUILD_PLATFORM_PASS ssh $BUILD_USER@$BUILD_PLATFORM_ADDRESS -p $BUILD_PLATFORM_PORT "$cmd")
echo "ARCHITECTURE=$ARCHITECTURE"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

if [ -z "${ARCHITECTURE}" ]; then
    echo -e "${RED}Error${NC}: There is some problem with your target HW.."
    exit 1
fi

OUTPUT_PATH="../../build/$ARCHITECTURE"
echo "OUTPUT_PATH=$OUTPUT_PATH"
mkdir -p $OUTPUT_PATH
rm -rf $OUTPUT_PATH/{*,.*}


PROJECT_NAME=$(cat package/DEBIAN/control | grep 'Package:' | awk '{print$2}')
version=$(cat package/DEBIAN/control | grep 'Version:' | awk '{print$2}')

echo "Copy Debian package to build folder.."
cp -r package $OUTPUT_PATH

PACKAGE_PATH="$OUTPUT_PATH/package"

BUILD_PATH="~/build-dir-$PROJECT_NAME"
DIST_PATH="~/build-dir-$PROJECT_NAME/dist"
EXE_NAME="$PROJECT_NAME"


#copy source to build platform:
cmd="mkdir -p $BUILD_PATH"
sshpass -p $BUILD_PLATFORM_PASS ssh $BUILD_USER@$BUILD_PLATFORM_ADDRESS -p $BUILD_PLATFORM_PORT "$cmd" 
sshpass -p $BUILD_PLATFORM_PASS scp -P $BUILD_PLATFORM_PORT ../src/*.* $BUILD_USER@$BUILD_PLATFORM_ADDRESS:$BUILD_PATH

#compile source
cmd1="--add-data \"config.yaml:.\""
cmd2="--distpath $DIST_PATH"
cmd3="--specpath $BUILD_PATH"
cmd4="-d all"
cmd="pyinstaller --onefile -y -n '$EXE_NAME' $cmd1 $cmd2 $cmd3 $cmd4 --clean $BUILD_PATH/main.py" 
echo $cmd
sshpass -p $BUILD_PLATFORM_PASS ssh $BUILD_USER@$BUILD_PLATFORM_ADDRESS -p $BUILD_PLATFORM_PORT "$cmd" 

echo "coping result to local path..."
EXE_OUTPUT_PATH="$PACKAGE_PATH/opt/$PROJECT_NAME"
mkdir -p $EXE_OUTPUT_PATH
sshpass -p $BUILD_PLATFORM_PASS scp -P $BUILD_PLATFORM_PORT $BUILD_USER@$BUILD_PLATFORM_ADDRESS:$DIST_PATH/$EXE_NAME $EXE_OUTPUT_PATH

# echo "cleaning remote path..."
# cmd="rm -rf $BUILD_PATH"
# ssh $BUILD_USER@$BUILD_PLATFORM_ADDRESS -p $BUILD_PLATFORM_PORT "$cmd" 

cp ../../project/src/config.yaml $PACKAGE_PATH/etc/$PROJECT_NAME/

# For test on the local machine
mkdir -p ~/$PROJECT_NAME/
cp ../../project/src/config.yaml ~/$PROJECT_NAME/

OUT_FULL_FILE_NAME="${OUTPUT_PATH}/${EXE_NAME}_${version}_${ARCHITECTURE}.deb"

dpkg-deb --root-owner-group -Z gzip -b $PACKAGE_PATH $OUT_FULL_FILE_NAME

if [ -f $OUT_FULL_FILE_NAME ]; then
   echo -e "${GREEN}Success${NC}: File $OUT_FULL_FILE_NAME was created."
else
   echo -e "${RED}Error${NC}: There is some problem with your build!"
fi

# sudo apt install hashdeep
md5deep -r $OUT_FULL_FILE_NAME > ${OUTPUT_PATH}/md5sums