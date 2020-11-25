#!/usr/bin/env bash
# File: guessinggame.sh  Author: Ahmed Qamesh
# Aim: Guess the number of files in a directory



allFiles=$(ls | wc -l)
guessNr=1
patt="^[0-9]*$"
max=100  #default value if input parameter is invalid
if [[ $1 =~ $patt ]] && [[ $1 -gt allFiles ]]
then
	max=$1
fi
echo "Guess the number of files in the $PWD directory. Enter an integer between 0 and $max"
while [[ $guess -ne $allFiles ]]
do 
	printf "Enter guess #$guessNr: "
    read -r guess
    if ([[ $guess =~ $patt ]] && [[ $guess -le $max ]] && [[ $guess -gt 0 ]])
    then
    if [[ $guess -lt allFiles ]]
 	then
		echo -e "The guess of $guess is too low\n"
		let guessNr=$guessNr+1
	elif [[ $guess -gt allFiles ]]
	then
		echo -e "The guess of $guess is too high\n"
		let guessNr=$guessNr+1
	fi
    else 
        echo "$guess is an invalid value.  Please enter an integer between 0 and $max"
    fi
done

if [[ guessNr -eq 1 ]] 
then
    echo -e "\nINCREDIBLE!!! You guessed correctly on your very first try!!\n"
else   
    echo -e "\nCongratulations! You guessed correctly with $guessNr tries!!!\n"
fi
