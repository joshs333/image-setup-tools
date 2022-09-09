# Nightmare Stick
The nightmare stick is a silly prank mostly serving to verify my understanding of the boot process and how to make bootable media / interact with grub.

The way it works is by adding a target called [nightmare@.service](overlay/etc/systemd/system/nightmare@.service), which basically runs [enter_sandman.sh](overlay/home/user/nightmare/enter_sandman.sh) and pipes the output to a tty.

The default base-os target is multi-user.service which would normally just run getty on each tty so to run the nightmare stick we mask the getty.target and instead add nightmare@tty1.service in the [grub.cfg](overlay/boot/grub/grub.cfg).

Of course this is just a nightmare, unplug the USB and reboot and the nightmare goes away :) no actually malicious acts are executed.
