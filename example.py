"""
This is a general implementation of the embedding of G from
the paper, the resulting embedding of \Z \wr (\Z_2 \wr \Z),
and generation of tikz code for Figure 1 in the paper.
"""

RIGHT = ">"
LEFT = "<"

# replace symbols a by symbols b in prefix of word
def replace_prefix(word, a, b):
    result = []
    for i in range(len(word)):
        if word[i] == a:
            result.append(b)
        else:
            break
    result.extend(word[i:])
    return result

def replace_suffix(word, a, b):
    word = list(reversed(word))
    word = replace_prefix(word, a, b)
    return list(reversed(word))

def read_belt(belt, pos):
    pos = pos % (2*len(belt))
    if pos < len(belt):
        return belt[pos][0]
    else:
        return belt[2*len(belt) - 1 - pos][1]
    
def write_belt(belt, pos, a):
    pos = pos % (2*len(belt))
    if pos < len(belt):
        belt[pos] = (a, belt[pos][1])
    else:
        pos = 2*len(belt) - 1 - pos
        belt[pos] = (belt[pos][0], a)

def apply_to_conveyor_belt(CA, belt):
    # represent belt positions by range(2 * len(belt))
    # where first half of coords are on top, and last ones
    # in reverse on bottom
    ret = belt[:]
    for i in range(2 * len(belt)):
        def oracle(r):
            #print("reading", i, r, belt, read_belt(belt, i+r))
            return read_belt(belt, i+r)
        write_belt(ret, i, CA(oracle))
    return ret

def deconstruct(Sigma, zero, word):

    # Recall that good words are: {>>, >C, BB, C<, <<, ><}.
    # We calculate bad positions, errors, walls and good positions etc..
    
    B = set([(s, t) for s in Sigma for t in Sigma])
    C = set([st for st in B if st[0] != zero or st[1] != zero])
    
    bad = set()
    for i in range(len(word) - 1):
        is_it_good = False
        a, b = word[i], word[i+1]
        if a == RIGHT and b == RIGHT:
            is_it_good = True
        elif a == RIGHT and b in C:
            is_it_good = True
        elif a in B and b in B:
            is_it_good = True
        elif a in C and b == LEFT:
            is_it_good = True
        elif a == LEFT and b == LEFT:
            is_it_good = True
        elif a == RIGHT and b == LEFT:
            is_it_good = True
        if not is_it_good:
            bad.add(i)
            bad.add(i+1)

    wall = set()
    for i in range(len(word) - 1):
        if word[i] != RIGHT and word[i+1] == RIGHT:
            wall.add(i+1)
        if word[i] == LEFT and word[i+1] != LEFT:
            wall.add(i)

    error = set()
    for i in bad:
        if i not in wall:
            error.add(i)

    good = set()
    for i in range(len(word)):
        if i not in bad:
            good.add(i)

    # this is so that there is a well-defined action on this word
    assert 0 in bad and len(word)-1 in bad

    # compute maximal good runs
    
    i = 0
    good_runs = []
    while i < len(word):
        # a good run starts, read it
        if i in good:
            start = i
            while i in good:
                i += 1
            end = i
            # interval convention left-closed right-open i.e. [a, b)
            good_runs.append((start, end))
        else:
            i += 1

    return B, C, bad, wall, error, good, good_runs

def compute_wall_and_prefix_info(wall, start, end):
    # compute the type of run, i.e. which sides have wall
    left_wall = start-1 in wall
    right_wall = end in wall
    
    # how many RIGHTs are in the beginning
    left_prefix = 0
    while word[start + left_prefix] == RIGHT:
        left_prefix += 1
    # how many LEFTs at the end    
    right_prefix = 0
    while word[end - 1 - right_prefix] == LEFT:
        right_prefix += 1
    return left_wall, right_wall, left_prefix, right_prefix
            
# Assume word has bad symbols on left and right.
# Apply a 0-to-0 CA through the encoding.
def apply_CA_pointy(CA, Sigma, zero, word):

    B, C, bad, wall, error, good, good_runs = deconstruct(Sigma, zero, word)

    # first compute the words to be rewritten, and actually rewrite later
    rewrites = []
    for (start, end) in good_runs:
        #segment = word[start:end]

        left_wall, right_wall, left_prefix, right_prefix = compute_wall_and_prefix_info(wall, start, end)
        
        # if no nonzero symbols, we do nothing here
        if left_prefix + right_prefix == end - start:
            rewrites.append(None)
            continue

        # simulated configuration after removing the RIGHT and LEFT affixes
        # note that left_prefix and right_prefix actually provide no
        # information per se, as they precisely record the boundaries
        # of the support
        simulated = [(zero, zero) for i in range(left_prefix)] + \
            word[start + left_prefix : end - right_prefix] + \
            [(zero, zero) for i in range(right_prefix)]

        result = apply_to_conveyor_belt(CA, simulated)
        
        if left_wall:
            result = replace_prefix(result, (zero, zero), RIGHT)
        if right_wall:
            result = replace_suffix(result, (zero, zero), LEFT)
        rewrites.append(result)

    final_result = word[:]
    for i, (start, end) in enumerate(good_runs):
        if rewrites[i] != None:
            final_result[start:end] = rewrites[i]
    return final_result

# simulated is a conveyor belt; we read it cyclically and try to find a word from u_words
# probably this is unnecessarily squarish in time complexity
def support_and_pos_from_belt(simulated, u_words, zero):
    #print("compute support and pos", simulated)
    for u in u_words:
        #print("try", u)
        for p in range(2*len(simulated)):
            #print("try pos", p)
            for i in range(2*len(simulated)):
                #print("try offset", i)
                if i < len(u):
                    if u[i] != read_belt(simulated, p+i):
                        break
                else:
                    if read_belt(simulated, p+i) != zero:
                        break
            else:
                return u, p

# if we have exactly one of the u_words on some conveyor belt, we shift and permute around
def apply_item_two(nzero, u_words, shifts, permu, Sigma, zero, word):

    # Recall that good words are: {>>, >C, BB, C<, <<, ><}.
    # We calculate bad positions, errors, walls and good positions.
    B, C, bad, wall, error, good, good_runs = deconstruct(Sigma, zero, word)

    # first compute the words to be rewritten, and actually rewrite later
    rewrites = []
    for (start, end) in good_runs:

        if end - start < nzero:
            rewrites.append(None)
            continue
        
        left_wall, right_wall, left_prefix, right_prefix = compute_wall_and_prefix_info(wall, start, end)

        # we will not apply these things at all in case of errors; or if tape too short
        if not left_wall or not right_wall:
            rewrites.append(None)
            continue

        # if no nonzero symbols, we do nothing here
        if left_prefix + right_prefix == end - start:
            rewrites.append(None)
            continue

        simulated = [(zero, zero) for i in range(left_prefix)] + \
            word[start + left_prefix : end - right_prefix] + \
            [(zero, zero) for i in range(right_prefix)]
        
        # compute the u_word on the belt and its position
        # safety is assumed; as otherwise returns first found and doesn't make sense
        res = support_and_pos_from_belt(simulated, u_words, zero)
        
        if res == None:
            rewrites.append(None)
            continue
            
        u_word, pos = res
        uidx = u_words.index(u_word)
        pos += shifts[uidx]

        reword = u_words[permu[uidx]]
        result = simulated[:]
        for p in range(2*len(result)):
            if p < len(reword):
                write_belt(result, pos + p, reword[p])
            else:
                write_belt(result, pos + p, zero)

        result = replace_prefix(result, (zero, zero), RIGHT)
        result = replace_suffix(result, (zero, zero), LEFT)
        
        rewrites.append(result)

    final_result = word[:]
    for i, (start, end) in enumerate(good_runs):
        if rewrites[i] != None:
            final_result[start:end] = rewrites[i]
    return final_result

# This is for tikzing configurations for the paper; specific to lamplighter example.
def tikz_line(word, width, height, at_height):
    #print(at_height)
    ret = ""

    mode = "squares"
        
    for i in range(len(word)):
        if word[i] == LEFT:
            ret += "\\node () at (%s, %s) {%s};\n" % ((i + 0.5)*width, -at_height-height/2, "\\footnotesize $<$")
        elif word[i] == RIGHT:
            ret += "\\node () at (%s, %s) {%s};\n" % ((i + 0.5)*width, -at_height-height/2, "\\footnotesize $>$")
        else:
            (a, b, c), (d, e, f) = word[i]
            for j, l in enumerate([a, b, c, d, e, f]):
                color = ["red", "green", "blue"][j%3]
                h = height/6*(j+1)
                if mode == "symbols":
                    ret += "\\node[%s] () at (%s, %s) {\\footnotesize %s};\n" % (color, (i + 0.5)*width, -at_height-h+height/12, l)
                else:
                    if l == 1:
                        ret += "\\fill[%s] (%s, %s) rectangle (%s, %s);\n" % (color, i*width, -at_height-h+height/6, (i+1)*width, -at_height-h)

    for i in range(len(word)):
        if word[i] not in [LEFT, RIGHT]:
            for j in range(5):
                h = height/6*(j+1)
                thickness = ""
                if j == 2:
                    thickness = "thick"
                ret += "\\draw[%s,%s] (%s, %s) -- (%s, %s);\n" % ("black", thickness, i*width, -at_height-h, (i+1)*width, -at_height-h)

    ret += "\\draw[thick, xstep=%s, ystep=%s, shift={(0,%s)}] (%s, %s) grid (%s, %s);\n" % (width, height, -at_height, 0, 0, len(word)*width, -height)
    
    return ret

# partial shift for \Z_2 wr \Z lamplighter embedding, with a dangling binary tape for clarity
def lamp_shift_l(config):
    a, b = config(0), config(1)
    return b[0], a[1], a[2]

def lamp_shift_r(config):
    a, b = config(0), config(-1)
    return b[0], a[1], a[2]

def lamp_flip(config):
    a = config(0)
    return a[0], (a[0] + a[1]) % 2, a[2]

zero = (0, 0, 0)
zz = (zero, zero)
alphabet = [(a, b, c) for a in [0,1] for b in [0,1] for c in [0,1]]

word = [zz, RIGHT, RIGHT, ((1,0,1), (0,0,0)), LEFT, LEFT, RIGHT, RIGHT, RIGHT, RIGHT, ((1,0,1), (0,0,0)), ((0,1,0), (0,0,0)), LEFT, zz, ((1,0,1), (0,0,0)), RIGHT, RIGHT, ((1,0,1), (0,0,0)), ((0,1,0), (1,0,0)), zz, LEFT, zz]

tikz = ""
width = 1
height = 1.5
pad = 0.2

print(word)
tikz += tikz_line(word, width, height, 0)

for (h, op_sym) in enumerate("RFLDDDDRFULULFLFLF"):
    
    op = None
    if op_sym == "R":
        op = lamp_shift_r
    elif op_sym == "L":
        op = lamp_shift_l
    elif op_sym == "F":
        op = lamp_flip
    if op != None:
        word = apply_CA_pointy(op, alphabet, zero, word)
    else:
        # the operations U and D are for the base \Z of the wreath product
        # we will only be shifting a single length-1 word, so singleton list with a length-1 tuple inside
        u_words = [[(1,0,1)]]
        if op_sym == "U":
            shifts = [1]
        elif op_sym == "D":
            shifts = [-1]
        permu = {0 : 0}
        word = apply_item_two(1, u_words, shifts, permu, alphabet, zero, word)
    tikz += tikz_line(word, width, height, (height+pad)*(h+1))
    tikz += "\\draw (%s,%s) edge[-stealth, bend right=45] (%s,%s);\n" % \
        (-0.25, -((height+pad)*(h+1)-height/2.1), -0.25, -((height+pad)*(h+1)+height/2.1))
    tikz += "\\node () at (%s, %s) {%s};\n" % (-1, -(height+pad)*(h+1), op_sym)
    print(op_sym)
    print(word)

with open("spacetime.tex", "w") as f:
    f.write(tikz)
#print(tikz)
    
print()
print()
print()
print()






