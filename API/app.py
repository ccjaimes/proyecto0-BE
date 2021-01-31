import os
import enum
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restful import Api, Resource
from datetime import datetime, date
from flask_jwt_extended import JWTManager
from flask_jwt_extended import (create_access_token, jwt_required, get_jwt_identity, get_raw_jwt)
from marshmallow_enum import EnumField

load_dotenv()

HOST=os.getenv("HOST")
DB=os.getenv("DB")
USER=os.getenv("USER")
PORT=os.getenv("PORT")
PW=os.getenv("PW")
SECRET=os.getenv("SECRET")
JWTSECRET=os.getenv("JWTSECRET")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://{}:{}@{}:{}/{}'.format(USER, PW, HOST, PORT, DB)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET
app.config['JWT_SECRET_KEY'] = JWTSECRET
db = SQLAlchemy(app)
ma = Marshmallow(app)
api = Api(app)
jwt = JWTManager(app)

# ENUMS

class EventoCat(enum.Enum):
    CONFERENCIA = "CONFERENCIA"
    SEMINARIO = "SEMINARIO"
    CONGRESO = "CONGRESO"
    CURSO = "CURSO"

class EventoForm(enum.Enum):
    PRESENCIAL = "PRESENCIAL"
    VIRTUAL = "VIRTUAL"

# MODELOS DE DATOS

class Usuario(db.Model):
    email = db.Column(db.String(100), primary_key=True)
    pw = db.Column(db.String(50))
    eventos = db.relationship('Evento', backref='usuario', lazy=True)

class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    categoria = db.Column(db.Enum(EventoCat))
    lugar = db.Column(db.String(100))
    direccion = db.Column(db.String(100))
    fechaInicio = db.Column(db.DateTime(), default=datetime.now)
    fechaFin = db.Column(db.DateTime(), default=datetime.now)
    forma = db.Column(db.Enum(EventoForm))
    usuario_email = db.Column(db.String(100), db.ForeignKey('usuario.email'), nullable=False)

# MARSHMALLOW SCHEMAS

class Usuario_schema(ma.Schema):
    class Meta:
        fields = ("email", "pw")

post_usuario_schema = Usuario_schema()
posts_usuarios_schema = Usuario_schema(many=True)

class Evento_schema(ma.Schema):
    categoria = EnumField(EventoCat, by_value=True)
    forma = EnumField(EventoForm, by_value=True)

    class Meta:
        fields = ("id", "nombre", "categoria", "lugar", "direccion", "fechaInicio", "fechaFin", "forma", "usuario_email")

post_evento_schema = Evento_schema()
posts_eventos_schema = Evento_schema(many=True)

# REST ENDPOINTS
class RecursoListarEventos(Resource):
    @jwt_required
    def get(self):
        email = get_jwt_identity()
        eventos = Evento.query.filter_by(usuario_email=email).order_by(db.desc(Evento.fechaInicio)).all()
        return posts_eventos_schema.dump(eventos)

    @jwt_required
    def post(self):
        email = get_jwt_identity()
        nuevo_evento = Evento(
            nombre = request.json['nombre'],
            categoria = request.json['categoria'],
            lugar = request.json['lugar'],
            direccion = request.json['direccion'],
            fechaInicio = request.json['fechaInicio'],
            fechaFin = request.json['fechaFin'],
            forma = request.json['forma'],
            usuario_email = email
        )
        db.session.add(nuevo_evento)
        db.session.commit()
        return post_evento_schema.dump(nuevo_evento)

class RecursoDetalleEvento(Resource):
    @jwt_required
    def get(self, id_evento):
        email = get_jwt_identity()
        evento = Evento.query.get_or_404(id_evento)
        if evento.usuario_email != email:
            return {'message':'No tiene acceso a este evento'}, 401
        return post_evento_schema.dump(evento)

    @jwt_required
    def put(self, id_evento):
        email = get_jwt_identity()
        evento = Evento.query.get_or_404(id_evento)
        if evento.usuario_email != email:
            return {'message':'No tiene acceso a este evento'}, 401

        if 'nombre' in request.json:
            evento.nombre = request.json['nombre']
        if 'categoria' in request.json:
            evento.categoria = request.json['categoria']
        if 'lugar' in request.json:
            evento.lugar = request.json['lugar']
        if 'direccion' in request.json:
            evento.direccion = request.json['direccion']
        if 'fechaInicio' in request.json:
            evento.fechaInicio = request.json['fechaInicio']
        if 'fechaFin' in request.json:
            evento.fechaFin = request.json['fechaFin']
        if 'forma' in request.json:
            evento.forma = request.json['forma']
        db.session.commit()
        return post_evento_schema.dump(evento)

    @jwt_required
    def delete(self, id_evento):
        email = get_jwt_identity()
        evento = Evento.query.get_or_404(id_evento)
        if evento.usuario_email != email:
            return {'message':'No tiene acceso a este evento'}, 401
        db.session.delete(evento)
        db.session.commit()
        return '', 204
        

class RecursoListarUsuarios(Resource):
    def post(self):
        if Usuario.query.filter_by(email=request.json['email']).first() is not None:
            return {'message': 'El correo {} ya está registrado'.format(request.json['email'])}
        nuevo_usuario = Usuario(
            email = request.json['email'],
            pw = request.json['pw']
        )

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            access_token = create_access_token(identity = request.json['email'])
            return {
                'message':'El correo {} ha sido registrado'.format(request.json['email']),
                'access_token':access_token
            }
        except:
            return {'message':'Ha ocurrido un error'}, 500
        
    
    def get(self):
        usuario = Usuario.query.get_or_404(request.json['email'])
        if usuario.pw != request.json['pw']:
            return {'message': 'Contraseña incorrecta'}
        try:
            access_token = create_access_token(identity = request.json['email'])
            return {
                'message':'Sesion iniciada',
                'access_token':access_token
            }
        except:
            return {'message':'Ha ocurrido un error'}, 500
    
    #TODO: Hacer put para cambiar contraseña


api.add_resource(RecursoListarEventos, '/eventos')
api.add_resource(RecursoListarUsuarios, '/usuarios')
api.add_resource(RecursoDetalleEvento, '/eventos/<int:id_evento>')

if __name__ == '__main__':
    app.run(debug=True)