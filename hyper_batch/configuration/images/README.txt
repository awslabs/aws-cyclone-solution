When deploying with cdk, place the Docker image directories in this folder. All directories need to contain a Dockerfile,
the start.sh script and needs to install the libraries needed for the worker agent.
See example-build-image/ for the base Dockerfile and start.sh script. You can modify these to
include your own artifacts and command operations but you need to keep the operations already there
as well in order for the worker to interact with hyper-batch scheduling layer.

The images.json config files then needs to refrence the right image folder in this directory and also provide a name for the image to create and distribute across enabled regions.