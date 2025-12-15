import os
import sys
sys.path.append(os.getcwd())

import uvicorn
from dotenv import load_dotenv

if __name__ == "__main__":

	env_file_name = os.path.join(os.getcwd(), "config", "env.config")
	if not os.path.exists(env_file_name):
		raise FileNotFoundError("env.config file is missing in the config folder.")
	
	load_dotenv(env_file_name)
	uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)