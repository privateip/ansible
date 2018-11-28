def iteritems_nested(d):
  def fetch (suffixes, v0) :
        if isinstance(v0, dict):
            for k, v in v0.items() :
                if v:
                    for i in fetch(suffixes + [k], v):  # "yield from" in python3.3
                        yield i
        else:
            yield (suffixes, v0)
  return fetch([], d)


def prepare_value(val):
    if isinstance(val, bool):
        return str(val).lower()
    elif isinstance(val, list):
        return ','.join([str(v) for v in val])
    else:
        return str(val)



def to_key(d, path=None) :

    f = dict( ('/'.join([str(o) for o in ks]), prepare_value(v)) for ks, v in iteritems_nested(d))

    d = dict([('/' + k, v) for k, v in f.items()])

    if path:
        objects = {}
        for key, value in d.items():
            key = '%s%s' % (path, key)
            objects[key] = value
        return objects
    else:
        return d
