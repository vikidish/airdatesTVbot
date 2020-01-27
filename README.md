# airdates TV bot

Display your shows from airdates.tv, get daily updates, search shows by name/date

python >=3.7.6  
requires >=sqlite 3.24.0 (upsert support), so won't work on CentOS 7 without compiling newer sqlite version

On 1st run:  

`python3 first_setup.py`  

crontab to send daily digest - run every hour:  

`5 * * * * python3 dailysendtask.py`

### Installing with Docker
Build from the main directory:  

`docker build -t airdatestvbot:1 .
`
Run the container:  

`docker run -d -it --name airdatestvbot --env-file .env -v {/path/to/datadir}:/usr/src/airdatesTVbot/data airdatestvbot:1`  

`--env-file .env` - is for Telegram secret, see .example.env  

`-v {/path/to/datadir}:/usr/src/airdatesTVbot/data` - mount the host directory in order not to lose db, cache and logs every docker run

For daily sends can use the following command in host crontab/other task schedule:  

`docker run -d --rm -it --name airdatestvbot_dailysend --env-file .env -v {/path/to/datadir}:/usr/src/airdatesTVbot/data airdatestvbot:1 python3 dailysendtask.py`
