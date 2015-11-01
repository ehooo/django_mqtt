# Select your backends from this list
BACKEND_CDB ?= no
BACKEND_MYSQL ?= no
BACKEND_SQLITE ?= no
BACKEND_REDIS ?= no
BACKEND_POSTGRES ?= no
BACKEND_LDAP ?= no
BACKEND_HTTP ?= yes
BACKEND_MONGO ?= no

# Specify the path to the Mosquitto sources here
MOSQUITTO_SRC = ../org.eclipse.mosquitto

# Specify the path the OpenSSL here
OPENSSLDIR = /usr
