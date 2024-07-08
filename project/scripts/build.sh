#!/bin/bash

# TODO: #:, pyyaml (>= 6.0.1), paho-mqtt (>= 2.1.0)

ARCHITECTURE="armhf"
PROJECT_NAME="gpio-mqtt"
VERSION="0.0.1"
BUILD_PLATFORM_ADDRESS=$1
BUILD_PLATFORM_PORT=$2
BUILD_PLATFORM_PASS=$3

# Info: you need sshpass packet for this script:
# sudo apt-get install sshpass

#build machine settings:
USER="root"
BUILD_PATH="~/build-dir-$PROJECT_NAME"
DIST_PATH="~/build-dir-$PROJECT_NAME/dist"
EXE_NAME="$PROJECT_NAME"

OUTPUT_PATH="../../build/$ARCHITECTURE"
PACKAGE_PATH="$OUTPUT_PATH/package"
EXE_OUTPUT_PATH="$PACKAGE_PATH/opt/$PROJECT_NAME"


# rm $EXE_OUTPUT_PATH/$EXE_NAME 2> /dev/null
# rm ../../build/${PROJECT_NAME}_${VERSION}_${ARCHITECTURE}.deb 2> /dev/null
rm -rf $OUTPUT_PATH

#copy source to build platform:
cmd="mkdir -p $BUILD_PATH"
sshpass -p $BUILD_PLATFORM_PASS ssh $USER@$BUILD_PLATFORM_ADDRESS -p $BUILD_PLATFORM_PORT "$cmd" 
sshpass -p $BUILD_PLATFORM_PASS scp -P $BUILD_PLATFORM_PORT ../src/*.* $USER@$BUILD_PLATFORM_ADDRESS:$BUILD_PATH

#compile source
cmd1="--add-data \"config.yaml:.\""
cmd2="--distpath $DIST_PATH"
cmd3="--specpath $BUILD_PATH"
cmd4="-d all"

cmd="pyinstaller --onefile -y -n '$EXE_NAME' $cmd1 $cmd2 $cmd3 $cmd4 --clean $BUILD_PATH/main.py" 
echo $cmd
sshpass -p $BUILD_PLATFORM_PASS ssh $USER@$BUILD_PLATFORM_ADDRESS -p $BUILD_PLATFORM_PORT "$cmd" 

echo "coping result to local path..."
mkdir -p $EXE_OUTPUT_PATH
sshpass -p $BUILD_PLATFORM_PASS scp -P $BUILD_PLATFORM_PORT $USER@$BUILD_PLATFORM_ADDRESS:$DIST_PATH/$EXE_NAME $EXE_OUTPUT_PATH

# echo "cleaning remote path..."
# cmd="rm -rf $BUILD_PATH"
# ssh $USER@$BUILD_PLATFORM_ADDRESS -p $BUILD_PLATFORM_PORT "$cmd" 

cp -a package $OUTPUT_PATH
cp ../../project/src/config.yaml $PACKAGE_PATH/etc/$PROJECT_NAME/

# For test on the local machine
mkdir ~/$PROJECT_NAME/
cp ../../project/src/config.yaml ~/$PROJECT_NAME/

version=$(cat $PACKAGE_PATH/DEBIAN/control | grep 'Version:' | awk '{print$2}')
OUT_FULL_FILE_NAME="${OUTPUT_PATH}/${EXE_NAME}_${version}_${ARCHITECTURE}.deb"

dpkg-deb --root-owner-group -Z gzip -b $PACKAGE_PATH $OUT_FULL_FILE_NAME
# sudo apt install hashdeep
md5deep -r $OUT_FULL_FILE_NAME > ${OUTPUT_PATH}/md5sums