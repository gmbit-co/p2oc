# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: verrpc/verrpc.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='verrpc/verrpc.proto',
  package='verrpc',
  syntax='proto3',
  serialized_options=b'Z,github.com/lightningnetwork/lnd/lnrpc/verrpc',
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x13verrpc/verrpc.proto\x12\x06verrpc\"\x10\n\x0eVersionRequest\"\xb9\x01\n\x07Version\x12\x0e\n\x06\x63ommit\x18\x01 \x01(\t\x12\x13\n\x0b\x63ommit_hash\x18\x02 \x01(\t\x12\x0f\n\x07version\x18\x03 \x01(\t\x12\x11\n\tapp_major\x18\x04 \x01(\r\x12\x11\n\tapp_minor\x18\x05 \x01(\r\x12\x11\n\tapp_patch\x18\x06 \x01(\r\x12\x17\n\x0f\x61pp_pre_release\x18\x07 \x01(\t\x12\x12\n\nbuild_tags\x18\x08 \x03(\t\x12\x12\n\ngo_version\x18\t \x01(\t2B\n\tVersioner\x12\x35\n\nGetVersion\x12\x16.verrpc.VersionRequest\x1a\x0f.verrpc.VersionB.Z,github.com/lightningnetwork/lnd/lnrpc/verrpcb\x06proto3'
)




_VERSIONREQUEST = _descriptor.Descriptor(
  name='VersionRequest',
  full_name='verrpc.VersionRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=31,
  serialized_end=47,
)


_VERSION = _descriptor.Descriptor(
  name='Version',
  full_name='verrpc.Version',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='commit', full_name='verrpc.Version.commit', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='commit_hash', full_name='verrpc.Version.commit_hash', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='version', full_name='verrpc.Version.version', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='app_major', full_name='verrpc.Version.app_major', index=3,
      number=4, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='app_minor', full_name='verrpc.Version.app_minor', index=4,
      number=5, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='app_patch', full_name='verrpc.Version.app_patch', index=5,
      number=6, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='app_pre_release', full_name='verrpc.Version.app_pre_release', index=6,
      number=7, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='build_tags', full_name='verrpc.Version.build_tags', index=7,
      number=8, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='go_version', full_name='verrpc.Version.go_version', index=8,
      number=9, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=50,
  serialized_end=235,
)

DESCRIPTOR.message_types_by_name['VersionRequest'] = _VERSIONREQUEST
DESCRIPTOR.message_types_by_name['Version'] = _VERSION
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

VersionRequest = _reflection.GeneratedProtocolMessageType('VersionRequest', (_message.Message,), {
  'DESCRIPTOR' : _VERSIONREQUEST,
  '__module__' : 'verrpc.verrpc_pb2'
  # @@protoc_insertion_point(class_scope:verrpc.VersionRequest)
  })
_sym_db.RegisterMessage(VersionRequest)

Version = _reflection.GeneratedProtocolMessageType('Version', (_message.Message,), {
  'DESCRIPTOR' : _VERSION,
  '__module__' : 'verrpc.verrpc_pb2'
  # @@protoc_insertion_point(class_scope:verrpc.Version)
  })
_sym_db.RegisterMessage(Version)


DESCRIPTOR._options = None

_VERSIONER = _descriptor.ServiceDescriptor(
  name='Versioner',
  full_name='verrpc.Versioner',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=237,
  serialized_end=303,
  methods=[
  _descriptor.MethodDescriptor(
    name='GetVersion',
    full_name='verrpc.Versioner.GetVersion',
    index=0,
    containing_service=None,
    input_type=_VERSIONREQUEST,
    output_type=_VERSION,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_VERSIONER)

DESCRIPTOR.services_by_name['Versioner'] = _VERSIONER

# @@protoc_insertion_point(module_scope)
