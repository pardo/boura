# boura
Tracking of object recognition and face matching

# extract frames from video using --scene
https://wiki.videolan.org/VLC_HowTo/Make_thumbnails/

# extract frames
vlc VID_20180912_083612.mp4 --video-filter=scene --vout=dummy --aout=dummy --scene-prefix=img- --scene-format=jpg --scene-ratio=10 --scene-path=. vlc://quit

# rotate left
mogrify -rotate -90 *.jpg

# upload to server
for i in *.jpg; do http --form POST :8000/upload/ dlib=1 image@"$i"; done

montage *.jpg -tile 10x -background "#111111" -geometry 200x200+2+2 montage.jpg


t d b f
t d b f
l r b f