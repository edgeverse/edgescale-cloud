# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright 2018-2019 NXP

from collections import OrderedDict

from flask import Blueprint, request, jsonify

from edgescale_pyutils.common_utils import bool_helper
from edgescale_pymodels.device_models import Host
from edgescale_pymodels.constants import UNAUTH_RESULT, STORAGE_PREFIX, BUCKET
from edgescale_pymodels.user_models import DccaUser
from edgescale_pymodels.solution_models import DccaAssSolutionImage, DccaModel, DccaSolutionAudit
from edgescale_pyutils.view_utils import get_oemid, get_json
from edgescale_pyutils.model_utils import as_dict, ctx
from edgescale_pyutils.param_utils import check_json, check_permission
from model import session
from model.ischema import SolutionSchema, DeviceShortSchema, DeviceSchema, SolutionAuditSchema
from utils import *

solution_bp = Blueprint("solution", __name__)


@solution_bp.route("", methods=["GET"])
def query_solutions():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    limit = request.args.get('limit') or 20
    offset = request.args.get('offset') or 0
    solution_name = request.args.get('solution')
    model_id = request.args.get('model_id')
    image = request.args.get('image')
    version = request.args.get('version')
    my_solution = bool_helper(request.args.get('my_solution'))

    results = OrderedDict()
    results['offset'] = offset
    results['limit'] = limit
    results['results'] = []

    total, solutions = DccaAssSolutionImage.query_solutions(solution_name, model_id, image, version,
                                                            my_solution, limit, offset)
    results['total'] = total
    if solutions:
        solutions = as_dict(solutions, SolutionSchema, many=True)
        for solution in solutions:
            if solution['owner_id'] == int(uid):
                solution['is_owner'] = True
            else:
                solution['is_owner'] = False
            del solution['owner_id']

            if solution['model']['owner_id'] == int(uid):
                solution['model']['is_owner'] = True
            else:
                solution['model']['is_owner'] = False
            del solution['model']['owner_id']

            if solution['model']['default_solution_id'] == solution['id']:
                solution['is_default'] = True
            else:
                solution['is_default'] = False
            del solution['model']['default_solution_id']

            results['results'].append(solution)

    return jsonify(results)


@solution_bp.route("", methods=["POST"])
def create_solution_view():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    solution_name = get_json(request).get('solution')
    model_id = get_json(request).get('model_id')
    version = get_json(request).get('version')
    image = get_json(request).get('image')
    url = get_json(request).get('url')
    is_signed = bool_helper(get_json(request).get('is_signed'))
    is_default = bool_helper(get_json(request).get('is_default'))
    have_installer = bool_helper(get_json(request).get('have_installer'))

    exceed_flag, max_limit_size = DccaAssSolutionImage.check_solution_limit()
    if exceed_flag:
        return jsonify({
            'status': 'fail',
            'message': 'Up to max limit({}) you can create.'.format(max_limit_size)
        })

    if url:
        in_s3 = False
        image = url.split('/')[-1]
        if not image:
            return jsonify({
                'status': 'fail',
                'message': 'Bad URL format'
            })
    else:
        in_s3 = True
        s3_url = STORAGE_PREFIX + BUCKET
        url = '/'.join([s3_url, ctx.current_user.username, solution_name, str(model_id), image.split('.')[0],
                        version, image])

    if is_default:
        if not DccaModel.check_model_owner(model_id):
            return jsonify({
                'status': 'fail',
                'message': 'Not the model owner, cannot set default'
            })

        if DccaModel.check_model_permission(model_id):
            return jsonify({
                'status': "fail",
                'message': "Can't set private solution as default solution of public model"
            })

    solution = DccaAssSolutionImage(solution_name, model_id, image, version, url, uid,
                                    in_s3, is_signed, have_installer)
    try:
        session.add(solution)
        session.commit()
    except Exception as e:
        err_msg = "Fail to create solution. {}".format(str(e))
        raise DCCAException(err_msg)

    solution_id = solution.id
    if is_default:
        solution.model.default_solution_id = solution_id
        try:
            session.commit()
        except Exception as e:
            err_msg = "Fail to set default solution. {}".format(str(e))
            raise DCCAException(err_msg)

    return jsonify({
        'id': solution_id,
        'status': 'success',
        'message': 'Success to create solution'
    })


@solution_bp.route("", methods=["PUT"])
def update_solution():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    solution_id = get_json(request).get('id')
    url = get_json(request).get('url')
    is_default = bool_helper(get_json(request).get('is_default'))

    is_owner = DccaAssSolutionImage.is_solution_owner(solution_id)
    if not is_owner:
        return jsonify({
            'status': 'fail',
            'message': 'Solution not exist or you are not permit to access'
        })

    image = url.split('/')[-1]
    if not image:
        return jsonify({
            'status': 'fail',
            'message': 'Bad URL format'
        })

    solution = DccaAssSolutionImage.query_by_id(solution_id)
    solution.image = image
    solution.link = url
    if is_default:
        if not DccaModel.check_model_owner(solution.model_id):
            return jsonify({
                'status': "fail",
                'message': "Not the model owner, can't set default solution"
            })

        if solution.is_public != DccaModel.check_model_permission(solution.model_id):
            return jsonify({
                'status': "fail",
                'message': "Solution and model have different permission, can't set default solution"
            })
        solution.model.default_solution_id = solution_id
    else:
        solution.model.default_solution_id = None

    try:
        session.commit()
    except Exception as e:
        err_msg = "Fail to update solution. {}".format(str(e))
        raise DCCAException(err_msg)

    return jsonify({
        'id': solution_id,
        'status': 'success',
        'message': 'Update the solution successfully'
    })


@solution_bp.route("", methods=["DELETE"])
def delete_solution():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    solution_id = get_json(request).get('id')

    if not DccaAssSolutionImage.is_solution_owner(solution_id):
        return jsonify({
            'status': "fail",
            'message': "Solution not exist or you are not permit to access."
        })

    if DccaAssSolutionImage.check_solution_permission(solution_id):
        return jsonify({
            'status': "fail",
            'message': "Can't delete public solution, change it to private solution then delete it"
        })

    if DccaModel.is_bind_solution(solution_id):
        return jsonify({
            'status': "fail",
            'message': "Fail to delete model's default solution. Edit solution to remove the default setting."
        })

    solution = DccaAssSolutionImage.query_by_id(solution_id)
    try:
        solution.remove(BUCKET)
        session.commit()
    except Exception as e:
        err_msg = "Fail to delete solution. {}".format(str(e))
        raise DCCAException(err_msg)

    return jsonify({
        'status': 'success',
        'message': 'Delete solution successfully'
    })


@solution_bp.route("/images/names", methods=["GET"])
def query_image_name():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    image_names = DccaAssSolutionImage.query_solution_image_names()

    return jsonify(image_names)


@solution_bp.route("/images/versions", methods=["GET"])
def query_image_version():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    versions = DccaAssSolutionImage.query_solution_image_versions()

    return jsonify(versions)


@solution_bp.route("/names", methods=["GET"])
def query_solution_name():
    """
    Get all the owner's solutions
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    solution_names = DccaAssSolutionImage.query_solution_names()

    return jsonify(solution_names)


@solution_bp.route("/names", methods=["POST"])
def check_solution_name():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    check_json(request)
    solution_name = get_json(request).get('solution')
    model_id = get_json(request).get('model_id')

    ctx.current_user = DccaUser.get_by_id(uid)

    is_exist = DccaAssSolutionImage.check_solution_name(solution_name, model_id)
    if not is_exist:
        return jsonify({
            'status': 'success',
            'message': 'solution name not exist'
        })
    else:
        return jsonify({
            'status': 'fail',
            'message': 'solution name already exists'
        })


@solution_bp.route("/statistics", methods=["GET"])
def query_solutions_statistics():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    results = {}
    statistics = Host.query_ota_statistics()
    if statistics:
        statistics = as_dict(statistics, DeviceShortSchema, many=True)
        for stat in statistics:
            solution = stat['solution']
            if solution["id"] not in results:
                results[solution["id"]] = {}
                results[solution["id"]].update(solution)
                results[solution["id"]]["count"] = 1
            else:
                results[solution["id"]]["count"] += 1

    return jsonify(list(results.values()))


@solution_bp.route("/statistics/devices", methods=["GET"])
def query_devices_by_solution():
    """
    To-Do: need improvement
    """
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    solution_id = request.args.get('solution_id')
    limit = request.args.get('limit') if request.args.get('limit') else 200
    offset = request.args.get('offset') if request.args.get('offset') else 0
    results = OrderedDict()
    results['limit'] = limit
    results['offset'] = offset
    results['results'] = []

    total, devices = Host.query_ota_devices(solution_id, limit, offset)
    results['total'] = total
    if devices:
        devices = as_dict(devices, DeviceSchema, many=True)
        for device in devices:
            device_status = query_one_device_status(device['name'])
            device.update(device_status)
            results['results'].append(device)

    return jsonify(results)


@solution_bp.route("/<solution_id>", methods=["GET"])
def query_one_solution(solution_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    solution = as_dict(DccaAssSolutionImage.get(solution_id), SolutionSchema)

    if solution['owner_id'] == int(uid):
        solution['is_owner'] = True
    else:
        solution['is_owner'] = False
    del solution['owner_id']

    if solution['model']['owner_id'] == int(uid):
        solution['model']['is_owner'] = True
    else:
        solution['model']['is_owner'] = False
    del solution['model']['owner_id']

    if solution['id'] == solution['model']['default_solution_id']:
        solution['is_default'] = True
    else:
        solution['is_default'] = False
    del solution['model']['default_solution_id']

    return jsonify(solution)


@solution_bp.route("/tags", methods=["GET"])
def query_tags():
    request.cursor.execute(query_all_existing_tags_sql)
    tags = request.cursor.fetchall()
    results = []

    for tag in tags:
        results.append(tag[0])

    return jsonify(results)


@solution_bp.route("/tags", methods=["POST"])
def add_tags():
    check_json(request)
    solution_id = get_json(request).get('solution_id')
    tag_list = get_json(request).get('tag_name', [])

    if not isinstance(tag_list, (list, tuple)):
        return jsonify({
            "status": "fail",
            "message": "tag_name type is array."
        })

    exist_tids, tag_names = query_exist_tag(request.cursor, tag_list)

    bind_tids = query_solution_has_tag_ids(request.cursor, solution_id, exist_tids)
    if not tag_names and len(bind_tids) == len(exist_tids):
        return jsonify({
            'status': 'success',
            'message': 'Success to attach tag to solution'
        })

    new_tids = create_tags(request.cursor, tag_names)

    unbind_tids = [val for val in exist_tids if val not in bind_tids]
    unbind_tids.extend(new_tids)

    ids = bind_solution_with_tags(request.cursor, solution_id, unbind_tids)
    if len(ids) == len(unbind_tids):
        request.conn.commit()
        return jsonify({
            'status': 'success',
            'message': 'Success to attach tag to solution'
        })

    request.conn.rollback()
    return jsonify({
        "status": "fail",
        "message": 'Error to add tag to solution'
    })


@solution_bp.route("/tags", methods=["DELETE"])
def delete_tag():
    check_json(request)
    solution_id = get_json(request).get('solution_id')
    tag_name = get_json(request).get('tag_name')

    if not tag_name:
        return jsonify({
            'status': 'fail',
            'message': 'Tag name cannot be empty'
        })

    # Check if tag exist, if not exist, do nothing
    tag_id = query_tag(request.cursor, tag_name)
    if not tag_id:
        return jsonify({
            'status': 'success',
            'message': 'Solution does not have the tag'
        })

    # Remove tag from solution
    remove_tag_from_solution_command = remove_tag_from_solution_sql.format(sol_id=solution_id, tag_id=tag_id)
    try:
        request.cursor.execute(remove_tag_from_solution_command)
        request.conn.commit()
    except Exception:
        raise DCCAException('Fail to remove tag from solution')

    return jsonify({
        'status': 'success',
        'message': 'Success to remove tag from solution'
    })


@solution_bp.route("/audit", methods=["GET"])
def query_audit_requests():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    if not ctx.current_user.admin:
        return jsonify({
            'status': 'fail',
            'message': 'Not admin, cannot access'
        })

    limit = request.args.get('limit') or 20
    offset = request.args.get('offset') or 0
    filter_text = request.args.get('filter_text') or ''
    order_by = request.args.get('orderBy') or ''
    order_type = request.args.get('orderType') or 'desc'

    if order_type not in ['asc', 'desc']:
        return jsonify({
            'status': "fail",
            'message': "Invalid order type"
        })

    if order_by not in ['created_at', 'status', '']:
        return jsonify({
            'status': "fail",
            'message': "Invalid orderBy value"
        })

    results = OrderedDict()
    results['orderType'] = order_type
    results['orderBy'] = order_by
    results['offset'] = offset
    results['limit'] = limit
    results['results'] = []

    total, audits = DccaSolutionAudit.query_audits(filter_text, order_by, order_type, limit, offset)
    results['total'] = total
    if audits:
        results['results'] = as_dict(audits, SolutionAuditSchema, many=True)

    return jsonify(results)


@solution_bp.route("/audit", methods=["POST"])
def create_audit_request():
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)
    solution_id = get_json(request).get('solution_id')
    comments = get_json(request).get('description')
    permission = get_json(request).get('permission')

    if not DccaAssSolutionImage.is_solution_owner(solution_id):
        return jsonify({
            'status': "fail",
            'message': "Solution not exist or you are not permit to access."
        })

    solution = DccaAssSolutionImage.get(solution_id)
    if not DccaModel.check_model_permission(solution.model_id) and not solution.is_public:
        return jsonify({
            'status': "fail",
            'message': "Model is private, Fail ro create request."
        })

    if DccaModel.check_model_permission(solution.model_id) and solution.is_public:
        if DccaModel.is_bind_solution(solution_id):
            return jsonify({
                'status': "fail",
                'message': "Solution is default solution of public model, Fail to create request."
            })

    to_public = check_permission(permission)
    req = DccaSolutionAudit(uid, comments, solution_id, to_public)

    try:
        session.add(req)
        session.commit()
    except Exception as e:
        err_msg = "Fail to create request. {}".format(str(e))
        raise DCCAException(err_msg)

    return jsonify({
        "status": "success",
        "message": "Request has been created, please wait for approval",
        "id": req.id
    })


@solution_bp.route("audit/<audit_id>", methods=["POST"])
def handle_audit_request(audit_id):
    uid, err = get_oemid(request=request)
    if err is not None:
        return jsonify(UNAUTH_RESULT)

    ctx.current_user = DccaUser.get_by_id(uid)

    check_json(request)

    if not ctx.current_user.admin:
        return jsonify({
            'status': 'fail',
            'message': 'Not admin, cannot access'
        })

    action = get_json(request).get('action')

    audit = DccaSolutionAudit.get(audit_id)
    if action == 'accept':
        approved = True
        if audit.to_public:
            audit.solution.is_public = True
        else:
            audit.solution.is_public = False
    else:
        approved = False

    audit.approved = approved
    audit.status = True

    try:
        session.commit()
    except Exception as e:
        err_msg = "Fail to handle the audit request. {}".format(str(e))
        raise DCCAException(err_msg)

    return jsonify({
        'status': 'success',
        'message': 'Handle the audit request successfully'
    })
