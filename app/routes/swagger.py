from flask import jsonify
from flask_swagger import swagger

from app import application


@application.route('/swagger')
def get_swagger():
    swag = swagger(application)
    swag['info']['version'] = "1.0"
    swag['info']['title'] = "ObjeXplain"
    swag['tags'] = {
        'name': "ObjeXplain API",
        'description': "API Specification for the ObjeXplain Web Application",
    }
    # TODO: finish all schemas: https://swagger.io/docs/specification/data-models/data-types/
    swag["components"] = {"schemas": {}, "requestBodies": {}}
    swag_schemas = swag["components"]["schemas"]
    swag_schemas['User'] = {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            },
            "name": {
                "type": "string"
            },
            "email": {
                "type": "string"
            },
            "password": {
                "type": "string"
            },
            "role": {
                "type": "string",
                "description": "The type and Berechtigungen of the User",
                "enum": [
                    "ADMIN",
                    "ANNOTATOR"
                ]
            },
            "active": {
                "type": "boolean"
            }
        }
    }
    swag_schemas['Image Document'] = {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            },
            "name": {
                "type": "string"
            },
            "fname": {
                "type": "string"
            },
            "image": {
                "type": "string",
                "format": "byte",
            },
            "width": {
                "type": "integer"
            },
            "height": {
                "type": "integer"
            },
            "prio": {
                "type": "number"
            },
            "objIds": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "objects": {
                "type": "array",
                "items": {
                    "type": "Detected Object"
                }
            },
            "userFinishedIds": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "finishedUsers": {
                "type": "array",
                "items": {
                    "type": "User"
                }
            },
            "userStartedIds": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "startedUsers": {
                "type": "array",
                "items": {
                    "type": "User"
                }
            },
            "updatedAt": {
                "type": "string"
            },
            "createdAt": {
                "type": "string"
            },
        }
    }
    swag_schemas['Detected Object'] = {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            },
            "docId": {
                "type": "string"
            },
            "doc": {
                "type": "Image Document"
            },
            "labelId": {
                "type": "string"
            },
            "label": {
                "type": "Label"
            },
            "tlx": {
                "type": "integer"
            },
            "tly": {
                "type": "integer"
            },
            "brx": {
                "type": "integer"
            },
            "bry": {
                "type": "integer"
            },
            "annotationIds": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "annotations": {
                "type": "array",
                "items": {
                    "type": "Annotation"
                }
            },
            "createdBy": {
                "type": "string"
            },
            "creator": {
                "type": "User"
            },
            "updatedAt": {
                "type": "string"
            },
            "createdAt": {
                "type": "string"
            },
        }
    }
    swag_schemas['Annotation'] = {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            },
            "objId": {
                "type": "string"
            },
            "object": {
                "type": "Detected Object"
            },
            "text": {
                "type": "string"
            },
            "tokens": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "conceptMask": {
                "type": "array",
                "items": {
                    "type": "integer"
                }
            },
            "conceptIds": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "concepts": {
                "type": "array",
                "items": {
                    "type": "Concept"
                }
            },
            "createdBy": {
                "type": "string"
            },
            "creator": {
                "type": "User"
            },
            "updatedAt": {
                "type": "string"
            },
            "createdAt": {
                "type": "string"
            }
        }
    }
    swag_schemas['Label'] = {
        "type": "object",
        "properties": {
            "_id": {
                "type": "string"
            },
            "name": {
                "type": "string"
            },
            "nameTokens": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "labelIdx": {
                "type": "integer"
            },
            "category": {
                "type": "string"
            },
            "createdAt": {
                "type": "string"
            }
        }
    }
    swag_bodies = swag["components"]["requestBodies"]
    swag_bodies['LabelBody'] = {
        "description": "A JSON object containing label information",
        "required": "true",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "labelIdx": {  # FIXME: remove idx, because this is determined automatically
                            "type": "integer"
                        },
                        "category": {
                            "type": "string"
                        }
                    }
                }
            }
        }
    }
    # TODO: finish all paths: https://swagger.io/docs/specification/paths-and-operations/
    # TODO: show the actual JSON result schema that you get when getting a HTTP 404 and 400 (and also show how a regular 200 result is wrapped).
    #  Probably need to create a NotFound-Schema and one OK-Schema for each entity.
    # TODO: creat a post request for label to input the label info that is saved in RESTClient firefox
    swag_paths = swag["paths"] = {}
    swag_paths['/annotate'] = {
        "post": {
            "tags": [
                "Insert a new Annotated Object"
            ],
            "summary": "Create a new Object with a single annotation",
            "requestBody": {
                "description": "Post a new Detected Object with the given Annotation into the specified Image Document",
                "required": "true",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/Annotation"
                        }
                    }
                }
            },
            "responses": {
                "201": {
                    "description": "Created",
                    "schema": {
                        "$ref": "#/components/schemas/Detected Object"
                    }
                },
                "404": {
                    "description": "NOT FOUND"
                }
            }
        },
        "put": {
            "tags": [
                "Insert a new Annotation"
            ],
            "summary": "Add annotation",
            "requestBody": {
                "description": "Annotate the specified Detected Object with a new Annotation",
                "required": "true",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/Annotation"
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "OK",
                    "schema": {
                        "$ref": "#/components/schemas/Annotation"
                    }
                },
                "404": {
                    "description": "NOT FOUND",
                    "schema": {
                        "$ref": "#/components/schemas/Annotation"
                    }
                }
            }
        },
        "get": {
            "tags": [
                "Search Annotations"
            ],
            "summary": "Search annotations by a an Annotation ID",

            "responses": {
                "200": {
                    "description": "OK",
                    "schema": {
                        "$ref": "#/components/schemas/Annotation"
                    }
                },
                "404": {
                    "description": "NOT FOUND",
                    "schema": {
                        "$ref": "#/components/schemas/Annotation"
                    }
                }
            }
        }
    }
    swag_paths['/annotate/search'] = {
        "get": {
            "tags": [
                "Search Annotations"
            ],
            "summary": "Search annotations by a regular expression",

            "responses": {
                "200": {
                    "description": "OK",
                    "schema": {
                        "$ref": "#/components/schemas/Annotation"
                    }
                },
                "404": {
                    "description": "NOT FOUND",
                    "schema": {
                        "$ref": "#/components/schemas/Annotation"
                    }
                }
            }
        }
    }
    swag_paths['/annotate/annotator'] = {
        "get": {
            "tags": [
                "Search Annotations"
            ],
            "summary": "Search annotations written by the annotator with the given User ID",

            "responses": {
                "200": {
                    "description": "OK",
                    "schema": {
                        "$ref": "#/components/schemas/Annotation"
                    }
                },
                "404": {
                    "description": "NOT FOUND",
                    "schema": {
                        "$ref": "#/components/schemas/Annotation"
                    }
                }
            }
        }
    }
    swag_paths['/idoc'] = {
        "get": {
            "tags": [
                "Search Image Documents"
            ],
            "summary": "Get the list of all Image Document Information (w/o image data)",

            "responses": {
                "200": {
                    "description": "OK",
                    "schema": {
                        "$ref": "#/components/schemas/Image Document"
                    }
                },
                "404": {
                    "description": "NOT FOUND",
                }
            }
        }
    }
    swag_paths['/label'] = {
        "post": {
            "tags": [
                "Insert a new Label"
            ],
            "summary": "Create a new Label",
            "requestBody": {
                "description": "Post a new Label to the Database",
                "required": "true",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/requestBodies/LabelBody"
                        }
                    }
                }
            },
            "parameters": [
                {
                    "in": "body",
                    "name": "body",
                    "description": "Label object that should be added to the Database",
                    "required": "true",
                    "schema": {
                        "$ref": "#/components/requestBodies/LabelBody"
                    },
                    "examples": {
                        "name": {
                            "summary": "Example of a object label as a single text string",
                            "value": "Hummingbird",
                        },
                        "labelIdx": {
                            "summary": "Example of an index",
                            "value": 0,
                        },
                        "category": {
                            "summary": "Example of a object category as a single text string",
                            "value": "bird",
                        },
                    }
                }
            ],
            "responses": {
                "201": {
                    "description": "Created",
                    "schema": {
                        "$ref": "#/components/schemas/Label"
                    }
                },
                "404": {
                    "description": "NOT FOUND"
                }
            }
        }
    }
    return jsonify(swag)
