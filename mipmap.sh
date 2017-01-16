#!/bin/sh

#How to smp this:
#for startat in 0 1 2 3 ; do cat mipmap.sh |sed "s/y++/y+=4/g"|sed "s/y=0/y=$startat/g" > mipmap_$startat.sh ; done
#for startat in 0 1 2 3 ; do nice -n 19 sh mipmap_$startat.sh & done


if [[ ! -f empty.png ]] ; then
    echo "Please provide an empty.png in the appropriate dimensions in this directory!"
    exit 1
fi
for zoom in {10..0}; do
    mkdir -p $zoom
    size="256x256"
    echo "Do not forget to set the right picture dimensions. It is set to $size."
    dimension=$((2**zoom))
    for (( y=0; y<dimension; y++ )) ; do
        for (( x=0; x<dimension; x++ )) ; do
            file1="./$((zoom+1))/$((x*2))-$((y*2)).png"
            file2="./$((zoom+1))/$((x*2 +1))-$((y*2)).png"
            file3="./$((zoom+1))/$((x*2))-$((y*2 +1)).png"
            file4="./$((zoom+1))/$((x*2+1))-$((y*2+1)).png"
            test -f "$file1" || file1="./empty.png"
            test -f "$file2" || file2="./empty.png"
            test -f "$file3" || file3="./empty.png"
            test -f "$file4" || file4="./empty.png"
            echo "generating ./$zoom/$x-$y.png"
            if [[ ! -f ./$zoom/$x-$y.png ]] ; then
                if [[ $file1 != "./empty.png" || $file2 != "./empty.png" || $file3 != "./empty.png" || $file4 != "./empty.png" ]]; then
            	    tmp_out_1=$(mktemp --suffix=.png)
            	    tmp_out_2=$(mktemp --suffix=.png)
                    convert +append "$file1" "$file2" $tmp_out_1
                    convert +append "$file3" "$file4" $tmp_out_2
                    convert -append $tmp_out_1 $tmp_out_2 ./$zoom/$x-$y.png
                    rm $tmp_out_1 $tmp_out_2
                    mogrify -resize $size ./$zoom/$x-$y.png
                fi
            fi
        done
    done
done
