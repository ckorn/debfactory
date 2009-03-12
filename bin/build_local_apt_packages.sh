cd $HOME/abs/post_build
apt-ftparchive packages -d /tmp/$1.db $1 | bzip2 -c > $1/Packages.bz2
