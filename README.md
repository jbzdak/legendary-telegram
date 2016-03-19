Backup scripts tool
===================

A simple backup tool that I designed for myself, probably useless to anyone 
who is not a developer. 

My backup requirements where 

* I need to understand what is happening
* Backup leaves my computer fully encrypted.
* No local copy of backup is saved (even temporalily) on my disk 
* This should be as fast as possible, ideally the local network bandwidth 
  should be a bottleneck
* Config files should be readable.  


My backup pipeline looks like that: 

* Files are compressed, encrypted, signed by GPG, and transferred to a local 
  nas server. 
* Some of these backups are then transferred to "the cloud"
 
So this tool is just a very fancy method of generating shell pipelines 
like that: 

    tar -c --to-stdout folder | pigz -i -b 1024 -p 4 --to-stdout -6 | gpg --encrypt --recipient id --compress-algo none | gpg --sign --local-user id --compress-algo none | ssh jb@nas 'cat > /data/file2016-03-19T13:45:22.472497.tar.gz.enc.sign && sync'
    
Then these shell pipelines are launched in parralel (or one by one).

### REQUIREMENTS

* Requirements depend on what operations you launch. 
* `bash` and `tar` are required alwasy
* If you want to compress files you need to install `pigz` or `pbzip2` 
  (parralel version of gzip and bzip2). The compression process 
  **is a bottleneck**, so parralelisation is required. 
* To use encryption you need to use ``gpg``.
 
    * To encrypt you need a gpg public key installed and imported to gpg instance. 
    * To sign you need an unencrypted private key installed to gpg, I strongly 
      suggest using this key only for signing. 
* To push to google cloud you need to push the files 
   
### TODO

1. Provide easy way to load backups (this is not supported) you need to 
   craft command by hand 
2. Add signature verification (and stripping) on the remote side (optionally)
3. Maybe add a explicit "post process steps to remote side", right now local 
   operations are concatenated by `|` and remote by `&&` which is inconsistent
   and inelastic. 
4. Add renice and ionice (optionally) to various parts of the pipeline to 
   have the system more usable duing backups. 
   
### Random remarks 
  
1. There is no guarantee of anything whatsoever. Especially I dont guarantee 
   that backups created by this will be recoverable. 
2. For now ``gpg`` is a performance bottleneck, as it is inherently single 
   process, this is alleviated slightly by the fact that multiple instances
   of pipeline can launched.    
 
Example config file (anonymized file I use): 
    
    execution:
      # How many parralel uploads to do 
      parralel_jobs: 2
      # A remote system to ssh into and dump backups
    connection:
      jbnas:
        host: jbnas
        remote_user: jb
        dest_folder: /data        
    # Two pipelines, one compresses and encrypts data, second also uploads to google cloud          
    pipelines:
      "compress encrypt":
        type: backup pipeline
        connection: ssh
        local:
          # Operations executed before ssh
          - operation: tar
          - operation: compress
            algorithm: gzip
            level: 6
          - operation: gpg encrypt
            key: B4B3E302D6531426
          - operation: gpg sign
            key: 3CBF323610829410
        remote:
          # Operations executed before after ssh
          - operation: save backup
            dest_file: "{dest_folder}/{dest_filename}{date}{extensions}"
          - operation: sync
      "compress encrypt push":
        type: backup pipeline
        connection: ssh
        local:
          - operation: tar
          - operation: compress
            algorithm: gzip
            level: 6
          - operation: gpg encrypt
            key: B4B3E302D6531426
          - operation: gpg sign
            key: 3CBF323610829410
        remote:
          - operation: save backup
            dest_file: "{dest_folder}/{dest_filename}{date}{extensions}"
          - operation: sync
          - operation: push to cloud
            sync: false
            target: gs://backups-nearline-monk-resurrection-vague-preserve/backups
            type: gcloud
    
    folders:
      # Jobs to do 
      - folders: /home/foo
        file_name: foo
        pipeline: compress encrypt
        connection: jbnas
      - folders: /home/bar
        file_name: bar
        pipeline: compress encrypt
        connection: jbnas
      - folders: /home/books
        file_name: books
        pipeline: "compress encrypt push"
        connection: jbnas
