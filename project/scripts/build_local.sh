#!/bin/bash

###
#this script should be uses into emulator for building Debian package
###

#cd "$(dirname "$(readlink -f "$0")")" || exit  # go to dir with this file

# TODO: #:, pyyaml (>= 6.0.1), paho-mqtt (>= 2.1.0)

ARCHITECTURE=$(dpkg --print-architecture)

OUTPUT_PATH="../../build/$ARCHITECTURE"
echo "OUTPUT_PATH=$OUTPUT_PATH"
mkdir -p $OUTPUT_PATH
rm -rf $OUTPUT_PATH/*

PROJECT_NAME=$(cat package/DEBIAN/control | grep 'Package:' | awk '{print$2}')
BUILD_VERSION=$(cat package/DEBIAN/control | grep 'Version:' | awk '{print$2}')

echo "Copy Debian package to build folder.."
cp -r package $OUTPUT_PATH

PACKAGE_PATH="$OUTPUT_PATH/package"

control=$(sed "s/Architecture: all/Architecture: $ARCHITECTURE/"  "$PACKAGE_PATH/DEBIAN/control")
echo "$control" > "$PACKAGE_PATH/DEBIAN/control"

BUILD_PATH="$HOME/build-dir-$PROJECT_NAME"
DIST_PATH="$HOME/build-dir-$PROJECT_NAME/dist"
EXE_NAME="$PROJECT_NAME"

#copy source to build platform:
mkdir -p $BUILD_PATH
cp -r ../src/* $BUILD_PATH

#compile source
cmd1="--add-data config.yaml:."
cmd2="--distpath $DIST_PATH"
cmd3="--specpath $BUILD_PATH"
pyinstaller --onefile --clean -y -n $EXE_NAME $cmd1 $cmd2 $cmd3  $BUILD_PATH/main.py

echo "coping result to local path..."
EXE_OUTPUT_PATH="$PACKAGE_PATH/opt/$PROJECT_NAME"
mkdir -p $EXE_OUTPUT_PATH
cp -r "$DIST_PATH/$EXE_NAME" "$EXE_OUTPUT_PATH"

OUT_FULL_FILE_NAME="${OUTPUT_PATH}/${EXE_NAME}_${BUILD_VERSION}_${ARCHITECTURE}.deb"

chmod +x "$PACKAGE_PATH/DEBIAN/preinst"
chmod +x "$PACKAGE_PATH/DEBIAN/postinst"
chmod +x "$PACKAGE_PATH/DEBIAN/prerm"
chmod +x "$PACKAGE_PATH/DEBIAN/postrm"

dpkg-deb --root-owner-group -Z gzip -b $PACKAGE_PATH $OUT_FULL_FILE_NAME

if [ -f $OUT_FULL_FILE_NAME ]; then
   echo -e "${GREEN}Success${NC}: File $OUT_FULL_FILE_NAME was created."
else
   echo -e "${RED}Error${NC}: There is some problem with your build!"
fi

rm -rf build

# 'sudo apt install hashdeep' or 'brew install md5deep'
md5deep -r $OUT_FULL_FILE_NAME > ${OUTPUT_PATH}/md5sums