Base ubuntu image
http://cdimage.ubuntu.com/ubuntu-base/releases/20.04/release/ubuntu-base-20.04.4-base-amd64.tar.gz


System Setup:
- partitioning
- initial bundle install

Online Stuff:
- just A/B / Rescue?


Use this command to see how long it's taking for USB stuff to write.
```
watch grep -e Dirty: -e Writeback: /proc/meminfo
```