#  Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read()

setup(
    name='hyper',
    version='0.1',
    author = 'Ludvig Nordstrom',
    author_email= 'ludvn@amazon.co.uk',
    py_modules=['hyper','qsub','qstat','qdel', 'qlog','commands'],
    packages=find_packages('.env/bin'),
    include_package_data=True,
    install_requires=[requirements],
    entry_points={
        'console_scripts': [
            'hyper = hyper:cli',
            'qsub = qsub:cli',
            'qstat = qstat:cli',
            'qdel = qdel:cli',
            'qlog = qlog:cli'
        ],
    },
)