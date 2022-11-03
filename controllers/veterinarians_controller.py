from types import NoneType
from flask import Blueprint, request
from init import db, bcrypt
from flask_jwt_extended import jwt_required, create_access_token
from models.veterinarian import VeterinarianSchema, Veterinarian
import gb
from datetime import timedelta


veterinarians_bp = Blueprint('veterinarians', __name__, url_prefix='/veterinarians')


# check if the veterinarian who has logged in has been authorized
def is_authorized_veterinarian(veterinarian_id):
    id = gb.get_veterinarian_id()
    if id == veterinarian_id:
        return True


# if the value is an empty string, convert it to null
def if_empty_convert_to_null(value):
    if len(value) == 0:
        return None
    else:
        return value


# return a correct value according to the data in the request
def nullable_value_converter(self, key):
    value = request.json.get(key)
    if isinstance(value, NoneType):
        return self.__dict__[key]
    else:
        return if_empty_convert_to_null(value)


# read all veterinarians and return the public information only
@veterinarians_bp.route('/')
def get_all_veterinarians():
    # get all records from the veterinarians table in the database
    veterinarians = gb.filter_all_records(Veterinarian)
    return VeterinarianSchema(many=True, only=['first_name', 'last_name', 'description', 'email', 'sex', 'languages']).dump(veterinarians)


# read all veterinarians and return all information, except password
@veterinarians_bp.route('/full_details/')
@jwt_required()
def get_all_veterinarians_full_details():
    if gb.is_admin():
        # get all records from the veterinarians table in the database
        veterinarians = gb.filter_all_records(Veterinarian)
        return VeterinarianSchema(many=True, exclude=['password']).dump(veterinarians)
    else:
        return {'error': 'You are not an administrator.'}, 401


# read one veterinarian and return the public information only
@veterinarians_bp.route('/<int:veterinarian_id>/')
def get_one_veterinarian(veterinarian_id):
    # get one record from the veterinarians table in the database with the given veterinarian id
    veterinarian = gb.required_record(Veterinarian, veterinarian_id)
    print(veterinarian)
    return VeterinarianSchema(only=['first_name', 'last_name', 'description', 'email', 'sex', 'languages']).dump(veterinarian)


# read one veterinarian and return all information, except password
@veterinarians_bp.route('/<int:veterinarian_id>/full_details/')
@jwt_required()
def get_one_veterinarian_full_details(veterinarian_id):
    if gb.is_admin() or is_authorized_veterinarian(veterinarian_id):
        # get one record from the veterinarians table in the database with the given veterinarian id
        veterinarian = gb.required_record(Veterinarian, veterinarian_id)
        return VeterinarianSchema(exclude=['password']).dump(veterinarian)
    else:
        return {'error': 'You are not authorized to view the information.'}, 401


# delete one veterinarian
@veterinarians_bp.route('/<int:veterinarian_id>/', methods=['DELETE'])
@jwt_required()
def delete_veterinarian(veterinarian_id):
    if gb.is_admin():
        # delete one record from the veterinarians table in the database with the given veterinarian id
        veterinarian = gb.required_record(Veterinarian, veterinarian_id)
        db.session.delete(veterinarian)
        db.session.commit()
        return {'msg': f'Veterinarian {veterinarian.first_name} {veterinarian.last_name} deleted successfully'}
    else:
        return {'error': 'You are not an administrator.'}, 401


# update one veterinarian
@veterinarians_bp.route('/<int:veterinarian_id>/', methods=['PUT', 'PATCH'])
@jwt_required()
def update_veterinarian(veterinarian_id):
    if gb.is_admin() or is_authorized_veterinarian(veterinarian_id):
        # update one record in the veterinarians table in the database with the given veterinarian id using the information contained in the request
        veterinarian = gb.required_record(Veterinarian, veterinarian_id)
        for key in list(request.json.keys()):
            if key in ['languages', 'description']:
                setattr(veterinarian, key, nullable_value_converter(veterinarian, key))
            else:
                setattr(veterinarian, key, gb.required_value_converter(veterinarian, key))
        db.session.commit()
        return VeterinarianSchema(exclude=['password']).dump(veterinarian)
    else:
        return {'error': 'You are not authorized to update the information.'}, 401


# create a new veterinarian
@veterinarians_bp.route('/register/', methods=['POST'])
def veterinarian_register():
    password_input = request.json.get('password')
    gb.validate_password(password_input)
    # add a new record to the veterinarians table in the database
    veterinarian = Veterinarian(
        first_name = request.json['first_name'],
        last_name = request.json['last_name'],
        email = request.json['email'],
        password = bcrypt.generate_password_hash(password_input).decode('utf-8'),
        sex = request.json['sex'],
        languages = if_empty_convert_to_null(request.json.get('languages')),
        is_admin = request.json['is_admin'],
        description = if_empty_convert_to_null(request.json.get('description'))
    )
    db.session.add(veterinarian)
    db.session.commit()
    return VeterinarianSchema(exclude=['password']).dump(veterinarian), 201


# veterinarian authentication
@veterinarians_bp.route('/login/', methods=['POST'])
def veterinarian_login():
    email=request.json['email']
    password = request.json['password']
    # get one record from the veterinarians table in the database with the given email
    veterinarian = gb.filter_one_record_by_email(Veterinarian, email)
    if veterinarian and bcrypt.check_password_hash(veterinarian.password, password):
        identity = ''.join(['V', str(veterinarian.id)])
        token = create_access_token(identity=identity, expires_delta=timedelta(days=1))
        return {'email': veterinarian.email, 'token': token}
    else:
        return {'error': 'Invalid email or passord'}, 401