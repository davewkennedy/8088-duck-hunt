;------------------------------------------------------------------------------------------
; PROGRAM 8
; David Kennedy
; ECE 3710 - Microprocessors
; Final Project - Skeet Shoot
; 10 December 2007
;------------------------------------------------------------------------------------------
ram_size                     equ 8192
rom_size                     equ 131072
prog_size                    equ 2048
red_led_seg                  equ 2000H
green_led_seg                equ 4000H
;------------------------------------------------------------------------------------------
; PPI
;------------------------------------------------------------------------------------------
porta                        equ 00H
portb                        equ 01H
portc                        equ 02H
PPI_Command_Port             equ 03H
PPI_Command_Word             equ 89H
;------------------------------------------------------------------------------------------
; PIT
;------------------------------------------------------------------------------------------
PIT_ToSpeaker_Port           equ 40H
PIT_ToPPI_Port               equ 41H
PIT_ToPIC_Port               equ 42H
PIT_Command_Port             equ 43H
PIT_ToSpeaker_Word           equ 36H
PIT_ToPPI_Word               equ 70H
PIT_ToPIC_Word               equ 0B6H     ; Just like 36H for Timer0, except the leading two bits are 10 instead of 00
;------------------------------------------------------------------------------------------
;PIC
;------------------------------------------------------------------------------------------
PIC_Port0                    equ 50H
PIC_Port1                    equ 51H
PIC_ICW1                     equ 13H      ; Edge Triggered, single mode using ICW4
PIC_ICW2                     equ 20H      ; Interrupts Vectors 20-27
PIC_ICW4                     equ 03H      ; Auto EOI and 8086 Mode
PIC_OCW1                     equ 7FH      ; Enable IR7 Only (vector 27H)
;------------------------------------------------------------------------------------------
; Some Other Constants
;------------------------------------------------------------------------------------------
Timer_Int_Vector             equ 27H      ; 30 msec Timer Interrupt Vector
PIT_Interval_Time            equ 60000    ; 30 msec at 2MHz Clock
pushButton_bit               equ 80H
;------------------------------------------------------------------------------------------
; Musical Note Frequencies
;------------------------------------------------------------------------------------------
See                          equ 7633     ; I may replace all of these at a later date with a table.
SeeSh                        equ 7220     ; There actually is a table below now - but I am not currently using it.
D                            equ 6802     ; The table is just hanging out.
DSh                          equ 6430
E                            equ 6060
F                            equ 5730
FSh                          equ 5390
G                            equ 5102
GSh                          equ 4819
A                            equ 4545
ASh                          equ 4291
B                            equ 4049
C5                           equ 3822
B5                           equ 3407
Pauz                         equ 0000
;------------------------------------------------------------------------------------------
; Code Startup Stuff
;------------------------------------------------------------------------------------------
SEGMENT .bss start=0
intvec0                      resd 256
theChamp                     resb 1
gameSpeed                    resb 1
random                       resb 1
not_port_c                   resb 1
bool_button_pressed          resb 1
bool_skeet_inAir             resb 1
bool_has_gunshot             resb 1
bool_hit_rightLED            resb 1
bool_game_over               resb 1
score                        resb 1
shotsLeft                    resb 1
highScore                    resb 1

code_seg                 equ 0F000H

SEGMENT .text start=100000H-prog_size
;------------------------------------------------------------------------------------------
; The Code!
;------------------------------------------------------------------------------------------
startup:
    call initialize
    call getDIPs
    call game

    waitForNewGame:
            test byte [bool_button_pressed], pushButton_bit
        jz continueWaiting
        jmp doneWaiting

        doneWaiting:
            mov byte [bool_button_pressed], 0     ; This Mov MUST be Here (for now)
            jmp startup
        continueWaiting:
        jmp waitForNewGame
;------------------------------------------------------------------------------------------
; Initialize Stuff        I will also eventually need PIC Stuff
;------------------------------------------------------------------------------------------
initialize:
        xor ax, ax
        mov bx, (100000H-rom_size)/16        ; Starting Segment of ROM Memory

        mov al, PPI_Command_Word             ; Set the PPI Command Word
        out PPI_Command_Port, al

        mov al, PIT_ToSpeaker_Word           ; Set the Timer 0 Command Word
        out PIT_Command_Port, al             ; MAKE SURE THAT YOU'RE OUTPUTTING TO pit_command_port AND NOT ppi_command_port

        mov al, PIT_ToPPI_Word               ; Set The Timer 1 Command Word
        out PIT_Command_Port, al

        mov al, PIT_ToPIC_Word
        out PIT_Command_Port, al
        mov al, PIT_Interval_Time & 0FFH ; For The PIC
        out PIT_ToPIC_Port, al
        mov al, PIT_Interval_Time >> 8
        out PIT_ToPIC_Port, al

        mov al, PIC_ICW1
        out PIC_Port0, al
        mov al, PIC_ICW2
        out PIC_Port1, al
        mov al, PIC_ICW4
        out PIC_Port1, al
        mov al, PIC_OCW1
        out PIC_Port1, al

        mov word [Timer_Int_Vector*4], ISR
        mov word [Timer_Int_Vector*4+2], code_seg

        mov ax, 00FFH                        ; Not sure why this is here - it's left over from the jingle bells program <-- Which Works!
        out PIT_ToPPI_Port, al
        out PIT_ToPPI_Port, al

        mov byte [theChamp], 00H
        mov byte [gameSpeed], 00H
        mov byte [random], 10H               ; A Value of 10, when loaded into cx and given to the Delay subroutine, will yield ~ 0.5 seconds
        mov byte [not_port_c], 00H
        mov byte [bool_button_pressed], 00H
        mov byte [bool_skeet_inAir], 00H
        mov byte [bool_has_gunshot], 00H
        mov byte [bool_hit_rightLED], 00H
        mov byte [bool_game_over], 00H
        mov byte [score], 00H
        mov byte [shotsLeft], 00H
        mov byte [highScore], 00H

        ret                                  ; return
;------------------------------------------------------------------------------------------
; Get The Values On The DIP Switches - The Game Speed and Championship Mode
;------------------------------------------------------------------------------------------
getDIPs:
    cli
    ;Get the Championship Status
    ;---------------------------------------------------------------------------
    in al, portc
    mov ah, al
    and ah, 08H
    mov [theChamp], ah
    cmp byte [theChamp], 08H
    je champMode
    mov al, 19H
    mov [shotsLeft], al
    jmp doneSettingChamp
    champMode:
        mov al, 0BH
        mov [shotsLeft], al
        jmp doneSettingChamp
    doneSettingChamp:
    ;---------------------------------------------------------------------------
    ; Get The Game Speed - All Of The Shifts Are To Truncate
    ;---------------------------------------------------------------------------
    in al, portc
    shl al, 1
    shl al, 1
    shl al, 1
    shl al, 1
    shl al, 1
    shr al, 1
    shr al, 1
    shr al, 1
    shr al, 1
    shr al, 1
    mov [gameSpeed], al
    xor byte [gameSpeed], 00000111B
    add byte [gameSpeed], 01H
    ;---------------------------------------------------------------------------
    sti
    ret
;------------------------------------------------------------------------------------------
; The Game Loop
;------------------------------------------------------------------------------------------
game:
    ; cli                                     <--------- I May Want This Here ..... Apparently It Works Without It
    ;call getDIPs

    cmp byte [score], 0AH
    je callEndTune
    cmp byte [shotsLeft], 00H
    je callEndTune

    jmp dontCallEndTune
    callEndTune:
        call endTune

    dontCallEndTune:

    cmp byte [bool_game_over], 0FFH
    je gameOver

    test byte [bool_button_pressed], pushButton_bit
    jz continue
    jmp buttonPressed

    buttonPressed:
        mov byte [bool_button_pressed], 0     ; This Mov MUST be Here (for now)
        mov ch, 0H
        mov cl, [random]
        dec byte [shotsLeft]
        call delay
        call launchSkeet
    continue:

    mov cx, 01H
    call delay
    jmp game

    gameOver:
    ret
;------------------------------------------------------------------------------------------
; The End Game Subroutine
;------------------------------------------------------------------------------------------
endTune:

    cmp byte [score], 0AH
    je playVictory
    jmp playDefeat

    playVictory:
        call playG
        call playPauz
        call playG
        call playPauz
        call playG
        call playC5
        call playC5
        call playC5
        call playC5


    jmp donePlayingTune

    playDefeat:
        call playD
        call playD
        call playD
        call playSeeSh
        call playSeeSh
        call playSeeSh
        call playSee
        call playSee
        call playSee

    donePlayingTune:

    mov byte [bool_game_over], 0FFH

    mov al, PIT_ToSpeaker_Word
    out PIT_Command_Port, al

    ret
;------------------------------------------------------------------------------------------
; A Delay To Extend Musical Notes, Light Displays, etc - i.e. Slow Things Down For Us Dumb Humans
;------------------------------------------------------------------------------------------
delay:
    loop_delay:
    mov al, PIT_ToPPI_Word
    out PIT_Command_Port, al
    mov al, 0FFH
    out PIT_ToPPI_Port, al
    out PIT_ToPPI_Port, al

    monitor:
        in al, portc
        and al, 40H                          ; The Mask For The Timer On The PPI
        cmp al, 40H
        jne monitor                          ; Stay in this loop until the timer has finished
    loop loop_delay
    ret
;------------------------------------------------------------------------------------------
; The Interrupt Service Routine
;------------------------------------------------------------------------------------------
ISR:
    push ax
    push cx

    inc byte [random]
    cmp byte [random], 30H
    je resetRandom
    continueISR:
    in al, portc                             ; Get the button state
    mov ah, al
    not al                                   ; Need button closures to be 1s not 0s
    xchg al, [not_port_c]                    ; Update not_port_c, get old copy in al
    xor al, [not_port_c]                     ; al is now the changes
    and al, [not_port_c]                     ; al contains only the closures
    or [bool_button_pressed], al             ; set the button (closure) flag
    test byte [bool_button_pressed], pushButton_bit
    jz dontShoot
    jmp shootAtSkeet

    shootAtSkeet:
        cmp byte [bool_skeet_inAir], 0FFH
        jne dontShoot

        mov byte [bool_has_gunshot], 0FFH

        mov byte [bool_button_pressed], 00H ; This Mov MUST be Here (for now)
        mov byte [bool_skeet_inAir], 00H

    dontShoot:

    pop cx
    pop ax
    iret

resetRandom:
    mov byte [random], 10H                   ; Just Reseting The Random Variable To Be ~ 0.5 Seconds
    jmp continueISR
;------------------------------------------------------------------------------------------
; Gunshot Noise
;------------------------------------------------------------------------------------------
gunshot:
        mov cx, 0FFFH
        gunshotNoise:

            mov ax, 7980
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 5522
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 3377
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 2187
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 6217
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 8811
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 1234
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 4500
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 8187
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 2860
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 9817
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al
            mov ax, 4920
            out PIT_ToSpeaker_Port, al
            mov al, ah
            out PIT_ToSpeaker_Port, al

            loop gunshotNoise

            mov al, PIT_ToSpeaker_Word
            out PIT_Command_Port, al

    ret
;------------------------------------------------------------------------------------------
; Launch A Skeet
;------------------------------------------------------------------------------------------
launchSkeet:
    mov byte [bool_skeet_inAir], 0FFH

    mov byte [bool_hit_rightLED], 07H
    mov ax, See
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax, 0DFFH
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx

    mov byte [bool_hit_rightLED], 07H
    cmp byte [bool_has_gunshot], 0FFH
    je mediaryGunShotJump
    mov ax, SeeSh
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax, 0EFFH
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx

    mov byte [bool_hit_rightLED], 07H
    cmp byte [bool_has_gunshot], 0FFH
    je mediaryGunShotJump
    mov ax, D
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax, 0F7FH
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx

    jmp over
    mediaryGunShotJump:                      ; This is just shitty programming - and I am ashamed of myself.
        jmp gunHasShot                       ; The je 's are too short to reach the gunshot.
                                             ; So they jump here, and this is a 'launching' point to the gunshot.
                                             ; And I'm not really sure how to fix that any other way - but I know there must be a better way.
    over:

    mov byte [bool_hit_rightLED], 07H
    cmp byte [bool_has_gunshot], 0FFH
    je mediaryGunShotJump
    mov ax, DSh
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax, 0FBFH
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx

    mov byte [bool_hit_rightLED], 07H
    cmp byte [bool_has_gunshot], 0FFH
    je mediaryGunShotJump
    mov ax, E
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax, 0FDFH
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx
    ;---------------------------------------------------------------------------

    mov byte [bool_hit_rightLED], 07H
    cmp byte [bool_has_gunshot], 0FFH
    je mediaryGunShotJump2
    mov ax, F
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax, 0FEFH
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx

    mov byte [bool_hit_rightLED], 07H
    cmp byte [bool_has_gunshot], 0FFH
    je mediaryGunShotJump2
    mov ax, FSh
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax, 0FF7H
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx

    jmp over2

    mediaryGunShotJump2:                     ; This is just shitty programming - and I am ashamed of myself.
        jmp gunHasShot                       ; The je 's are too short to reach the gunshot.
                                             ; So they jump here, and this is a 'launching' point to the gunshot.
                                             ; And I'm not really sure how to fix that any other way - but I know there must be a better way.
    over2:

    mov byte [bool_hit_rightLED], 07H
    cmp byte [bool_has_gunshot], 0FFH
    je mediaryGunShotJump2
    mov ax, G
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax, 0FFBH
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx
    cmp byte[bool_has_gunshot], 0FFH
    je mediaryGunShotJump2

    mov byte [bool_hit_rightLED], 08H
    cmp byte[bool_has_gunshot], 0FFH
    je mediaryGunShotJump2
    mov ax, GSh
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax, 0FFDH
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx
    ;---------------------------------------------------------------------------

    cmp byte [bool_has_gunshot], 0FFH
    je gunHasShot
    mov byte [bool_hit_rightLED], 07H
    cmp byte [bool_has_gunshot], 0FFH
    je gunHasShot
    mov ax, A
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax,  0FFEH
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx

    ;---------------------------------------------------------------------------

    mov byte [bool_hit_rightLED], 07H
    cmp byte [bool_has_gunshot], 0FFH
    je gunHasShot
    mov ax, ASh
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ax, 0FFFH
    out porta, al
    mov al, ah
    mov ah, [score]
    shl ah,1
    shl ah,1
    shl ah,1
    shl ah,1
    or al, ah
    out portb, al
    mov ch, 00H
    mov cl, [gameSpeed]
    call delay
    inc bx
    inc bx

    mov al, PIT_ToSpeaker_Word
    out PIT_Command_Port, al
    mov byte [bool_has_gunshot], 00H
    mov byte [bool_skeet_inAir], 00H
    jmp gunHasNotShot

    ;---------------------------------------------------------------------------

    gunHasShot:

        call gunshot

        mov al, 0FFH
        out porta, al

        mov al, [bool_hit_rightLED]
        or al, 03H
        cmp byte [bool_hit_rightLED], 08H
        je incrementScore
        jmp outputShotResults

        incrementScore:
            inc byte [score]

        outputShotResults:
            mov ah, [score]
            shl ah,1
            shl ah,1
            shl ah,1
            shl ah,1
            or al, ah
            out portb, al

        mov byte [bool_has_gunshot], 00H

    gunHasNotShot:

    ret
;------------------------------------------------------------------------------------------
; Subroutines For Various Notes - This Could Have Been Implemented Better - But It Works
;------------------------------------------------------------------------------------------
playSee:
    mov ax, See
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playSeeSh:
    mov ax, SeeSh
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playD:
    mov ax, D
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playDSh:
    mov ax, DSh
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playE:
    mov ax, E
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playF:
    mov ax, F
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playFSh:
    mov ax, FSh
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playG:
    mov ax, G
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playGSh:
    mov ax, GSh
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playA:
    mov ax, A
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playASh:
    mov ax, ASh
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playB:
    mov ax, B
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playC5:
    mov ax, C5
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playB5:
    mov ax, B5
    out PIT_ToSpeaker_Port, al
    mov al, ah
    out PIT_ToSpeaker_Port, al
    mov ch, 00H
    mov cl, 0FH
    call delay
    ret
playPauz:
    mov al, PIT_ToSpeaker_Word
    out PIT_Command_Port, al
    mov ch, 00H
    mov cl, 04H
    call delay
    ret

;------------------------------------------------------------------------------------------
; Some Reset Stuff
;------------------------------------------------------------------------------------------
times prog_size - 10H - ($-$$) db 0FFH

xor ax, ax
mov ds, ax
mov ss, ax
mov es, ax
mov sp, ram_size-2
jmp code_seg:startup
