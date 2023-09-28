from .middlewares import login_required
from flask import Flask, json, g, request
from app.regions.aws import RegionAWS as Region
from app.queues.aws import QueuesAWS as Queues
from app.queue.aws import QueueAWS as Queue
from app.clusters.aws import ClustersAWS as Clusters
from app.definitions.aws import DefinitionsAWS as Definitions
from app.definition.aws import DefinitionAWS as Definition
from app.batch.queues.aws import BatchQueueAWS as BatchQueue
from app.batch.jobs.aws import BatchJobAWS as BatchJob
from app.batch.compute.aws import BatchComputeAWS as BatchCompute
from app.jobs.aws import JobsAWS as Jobs
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/api/regions", methods=["GET"])
# @login_required
def get_regions():
    return json_response(Region().get_regions())


@app.route("/api/queues", methods=["GET"])
# @login_required
def get_queues():
    return json_response(Queues().get_queues())


@app.route("/api/queues/<string:name>", methods=["GET"])
# @login_required
def get_queue(name):
    return json_response(Queue(name=name).get_queue())


@app.route("/api/clusters", methods=["GET"])
# @login_required
def get_clusters():
    return json_response(Clusters().get_clusters())


@app.route("/api/jobs", methods=["GET"])
# @login_required
def get_current_jobs():
    return json_response(Jobs().get_current_jobs())


@app.route("/api/definitions", methods=["GET"])
# @login_required
def get_definitions():
    return json_response(Definitions().get_definitions())


@app.route("/api/definitions/<string:name>", methods=["GET"])
# @login_required
def get_definition(name):
    return json_response(Definition(name=name).get_definition())


@app.route("/api/definitions/<string:name>/purge_queue", methods=["PUT"])
# @login_required
def purge_definition_queue(name):
    return json_response(Definitions(name=name).purge_definition_queue())


@app.route("/api/batch/<string:region>/queues", methods=["GET"])
# @login_required
def get_batch_queues(region):
    return json_response(BatchQueue(region=region).get_batch_queues())


@app.route("/api/batch/<string:region>/queues/<string:name>/jobs", methods=["GET"])
# @login_required
def get_batch_jobs(region, name):
    return json_response(BatchJob(region=region, job_queue_name=name).get_batch_jobs())


@app.route("/api/batch/<string:region>/queues/<string:name>/jobs/purge_jobs", methods=["PUT"])
# @login_required
def purge_batch_jobs(region, name):
    return json_response(BatchJob(region=region, job_queue_name=name).purge_batch_jobs())


@app.route("/api/batch/<string:region>/queues/<string:name>/compute", methods=["GET"])
# @login_required
def get_batch_compute(region, name):
    return json_response(BatchCompute(region=region, job_queue_name=name).get_batch_compute())


def json_response(payload, status=200):
    return (json.dumps(payload), status, {"content-type": "application/json"})
