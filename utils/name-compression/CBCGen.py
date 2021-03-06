#!/usr/bin/env python
import sys
import os
from collections import defaultdict

filenames = sys.argv[1:]
if len(filenames) == 0:
  print "-- CBC table generation tool -- "
  print "Usage: ./CBCGen.py file1.txt file2.txt file3.txt ..."
  sys.exit(1)

hist = defaultdict(int)
def collect_top_entries(val):
  """
  Collect the most frequent substrings and organize them in a table.
  """
  # sort items by hit rate.
  lst = sorted(hist.items(), key=lambda x: x[1] , reverse=True)[0:val]
  # Strip out entries with a small number of hits.
  # These entries are not likely to help the compressor and can extend the compile
  # time of the mangler unnecessarily.
  lst = filter(lambda p: p[1] > 15 and len(p[0]) > 3, lst)
  return lst

def getTokens(line):
  """
  Split the incoming line into independent parts. The tokenizer has rules for
  extracting identifiers (strings that start with digits followed by letters),
  rules for detecting words (strings that start with upper case letters and
  continue with lower case letters) and rules to glue swift mangling tokens
  into subsequent words.
  """
  # String builder.
  sb = ""
  # The last character.
  Last = ""
  for ch in line:
    if Last.isupper():
      # Uppercase letter to digits -> starts a new token.
      if ch.isdigit():
        if len(sb) > 3:
          yield sb
          sb = ""
        sb += ch
        Last = ch
        continue
      # Uppercase letter to lowercase or uppercase -> continue.
      Last = ch
      sb += ch
      continue

    # Digit -> continue.
    if Last.isdigit():
      Last = ch
      sb += ch
      continue

    # Lowercase letter to digit or uppercase letter -> stop.
    if Last.islower():
      if ch.isdigit() or ch.isupper():
        if len(sb) > 4:
          yield sb
          sb = ""
        sb += ch
        Last = ch
        continue
      Last = ch
      sb += ch
      continue

    # Just append unclassified characters to the token.
    if len(sb) > 3:
      yield sb
      sb = ""
    sb += ch
    Last = ch
  yield sb

def addLine(line):
  """
  Extract all of the possible substrings from \p line and insert them into
  the substring dictionary. This method knows to ignore the _T swift prefix.
  """
  if not line.startswith("__T"): return

  # Strip the "__T" for the prefix calculations.
  line = line[3:]

  # Add all of the tokens in the word to the histogram.
  for tok in getTokens(line):
      hist[tok] += 1

# Read all of the input files and add the substrings into the table.
for f in filenames:
  for line in open(f):
    addLine(line.strip('\n').strip())

# Use these characters as escape chars.
escape_char0 = 'Y'
escape_char1 = 'J'

# notice that Y and J are missing because they are escape chars:
charset = r"0123456789_abcdefghijklmnopqrstuvwxyzABCDEFGHIKLMNOPQRSTUVWXZ$"
encoders = [c for c in charset] # alphabet without the escape chars.
enc_len = len(encoders)

# Take the most frequent entries from the table that fit into the range of
# our indices (assuming two characters for indices).
table = collect_top_entries(enc_len * enc_len)

# Calculate the reverse mapping between the char to its index.
index_of_char = ["-1"] * 256
idx = 0
for c in charset:
  index_of_char[ord(c)] = str(idx)
  idx+=1

class Trie:
  """
  This Trie data structure can generate C code for searching if a string is stored in the tree
  and what is the TableIdx that is associated with that string.
  """
  def __init__(self):
    self.TableIdx = None
    self.children = {}

  def add(self, word, TableIdx):
    # Place the table index at the end of strings.
    if len(word) == 0:
      self.TableIdx = TableIdx
      return

    first_letter = word[0]

    # Create a new entry in the Trie node if needed.
    if first_letter not in self.children:
      self.children[first_letter] = Trie()

    # Insert the rest of the string recursively.
    self.children[first_letter].add(word[1:], TableIdx)

  def generateHeader(self):
    return "// Returns the index of the longest substring in \p str that's shorter than \p n.\n" +\
           "int matchStringSuffix(const char* str, int n) {"

  def generateFooter(self):
    return "return -1; \n}"

  def generate(self, depth):
    """
    Generate a search procedure for the Trie datastructure.
    """
    sb = ""
    space = " " * depth
    for opt,node in self.children.iteritems():
      sb += space + "if ((%d < n) && (str[%d] == '%s')) {\n" % (depth, depth, opt)
      sb += space + node.generate(depth + 1)
      sb += space + "}\n"
    if self.TableIdx:
      sb += space + "return " + str(self.TableIdx) + ";\n"
    return sb

# Take only the key values, not the hit count
key_values = [p[0] for p in table]
# Array of string lengths.
string_length_table = map(lambda x: str(len(x)), key_values)
# Stringify the list of words that we use as substrings.
string_key_list = map(lambda x: "\""+ x + "\"", key_values)

# Add all of the substrings that we'll use for compression into the Trie.
TrieHead = Trie()
for i in xrange(len(key_values)): TrieHead.add(key_values[i], i)


# Generate the header file.

print "#ifndef SWIFT_MANGLER_CBC_TABLE_H"
print "#define SWIFT_MANGLER_CBC_TABLE_H"

print "// This file is autogenerated. Do not modify this file."
print "// Processing text files:", " ".join([os.path.basename(f) for f in filenames])

print "namespace CBC {"
print "// The charset that the fragment indices can use:"
print "const unsigned CharsetLength = %d;" % len(charset)
print "const char *Charset = \"%s\";" % charset
print "const int IndexOfChar[] =  {", ",".join(index_of_char),"};"
print "const char EscapeChar0 = '%s';" % escape_char0
print "const char EscapeChar1 = '%s';" % escape_char1
print "// The Fragments:"
print "const unsigned NumFragments = ", len(string_key_list), ";"
print "const char* CodeBook[] = {", ",".join(string_key_list),"};"
print "const unsigned CodeBookLen[] = {", ",".join(string_length_table),"};"
print TrieHead.generateHeader()
print TrieHead.generate(0)
print TrieHead.generateFooter()
print "} // namespace"
print "#endif /* SWIFT_MANGLER_CBC_TABLE_H */"
