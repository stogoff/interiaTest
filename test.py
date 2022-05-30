import paramiko

host = "gba.ee"
port = 22

username = "rs"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, port, username)

sftp = ssh.open_sftp()

path = "/home/rs/www/gba.ee/img/"
localpath = "images/meski-sygnet-obsidian-platerowany-srebrem-pr9252cc2970344d1918decc6.jpeg"
print(sftp.listdir(path))
sftp.put(localpath, path+localpath.split("/")[-1])

sftp.close()
ssh.close()
