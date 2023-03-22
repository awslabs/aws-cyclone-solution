export AWS_PROFILE="sso-myprofile"
export CYCLONE_STACKNAME="cylcone-stack-name"
source ~/venvs/310/bin/activate #activate python viritual environment if needed
FLASK_DEBUG=1 FLASK_APP="api/endpoints.py" flask run -p 4433 &
cd web
ng serve --port 8080 
