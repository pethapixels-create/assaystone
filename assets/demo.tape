# Record from a clean directory with the repository on PYTHONPATH:
#   mkdir -p /tmp/assaystone-demo && cd /tmp/assaystone-demo
#   PYTHONPATH=/path/to/assaystone vhs -o /path/to/assaystone/assets/demo.gif \
#     /path/to/assaystone/assets/demo.tape

Output assets/demo.gif

Set Shell "zsh"
Set FontFamily "Menlo"
Set FontSize 20
Set Width 1200
Set Height 760
Set Padding 20
Set BorderRadius 8
Set Theme "Dracula"
Set TypingSpeed 45ms

Type "python3 -m assaystone demo audit"
Enter
Sleep 5s

Type "clear"
Enter
Sleep 500ms

Type "python3 -m assaystone demo"
Enter
Sleep 6s

Type "clear"
Enter
Sleep 500ms

Type "python3 -m assaystone demo ops"
Enter
Sleep 6s
