def on_load(jarvis):
    jarvis.notify('Plugin de test chargé avec succès.')


def on_unload():
    pass


def bonjour(*args, **kwargs):
    return 'Bonjour depuis le système de plugins de J.A.R.V.I.S. NEO !'


COMMANDS = {
    'bonjour': bonjour,
}
