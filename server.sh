# Caddy Install for SSL
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl &&
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg &&
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list &&
sudo apt update &&
sudo apt install caddy &&
sudo systemctl status caddy &&

# Caddyfile
sudo echo "wouldyourather.ovh {
        request_body {
                max_size 20MB
        }

        # backend
        reverse_proxy /_event* localhost:8000
        reverse_proxy /_upload* localhost:8000
        reverse_proxy /socket.io* localhost:8000

        #frontend
        reverse_proxy localhost:3000
}" | sudo tee /etc/caddy/Caddyfile &&

sudo systemctl reload caddy && 

# Miniconda Install

wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh &&
bash Miniconda3-latest-Linux-x86_64.sh -b &&

# Conda env creation prep (VPS /tmp directory pointing)
export TMPDIR='/var/tmp'

# Environment creation
conda env create --file environment.yml &&
conda activate wouldyourather &&

# Reflex Setup
## Edit PIP reflex package to remove floating watermark
reflex init
cp reflex/would_you_rather_bot/assets/favicon.ico .web/public/favicon.ico

# Run App
reflex run --env prod
