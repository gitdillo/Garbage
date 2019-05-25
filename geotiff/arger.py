import sys, getopt
import re

def amap(f, l):
    return list(map(f, l))

def parseArgs(argv, args):
    aliases = []
    commands = []

    commandList = []

    required = {}

    for arg in args:
        opts = []
        setter = arg.get("setter")
        isInput = arg.get("input", False)

        if arg.get("alias"):
            for alias in arg["alias"]:
                aliases.append(alias + ":" if isInput == True else alias)
                opts.append(alias)
    
        command = arg["command"]
        commands.append(command + "=" if isInput == True else command)

        opts.append(command)
        commandList.append([opts, arg])

        if arg.get("required") == True:
            required[command] = arg

    opts, args = getopt.getopt(argv, aliases, commands)

    parsed = {}
    for opt, arg in opts:
        found = False
        opt = re.sub("^-+", "", opt)

        for commands in commandList:
            if found == True:
                break

            check, command = commands
            if opt in check:
                found = True
                k = command["command"]
                if required.get(k) != None:
                    del required[k]

                gotKey = command.get("key", False)
                key = command["command"] if gotKey == False else gotKey

                if command.get("input") == True:
                    parsed[key] = arg
                else:
                    parsed[key] = True

    missing = list(required.keys())
    if len(missing) > 0:
        raise Exception("Missing required keys: {0}".format(missing))

    return parsed

def printHelp(script, commands):
    print("python {0}".format(script))
    for cmd in commands:
        items = []

        aliases = cmd.get("alias", None)
        command = cmd.get("command")

        items.append("--" + command)
        if aliases != None:
            for alias in aliases:
                items.append("-" + alias)

        if cmd.get("input") == True:
            items.append("<input>")

        if cmd.get("required") == True:
            items.append("Required")

        example = cmd.get("example", None)
        if example != None:
            items.append("Example:")
            items.append(items[0])
            items.append(example)

        print("  " + " ".join(items))


