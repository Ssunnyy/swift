//===--- UnsafePointerLikeTypeTraits.h ------------------------------------===//
//
// This source file is part of the Swift.org open source project
//
// Copyright (c) 2014 - 2016 Apple Inc. and the Swift project authors
// Licensed under Apache License v2.0 with Runtime Library Exception
//
// See http://swift.org/LICENSE.txt for license information
// See http://swift.org/CONTRIBUTORS.txt for the list of Swift project authors
//
//===----------------------------------------------------------------------===//

#ifndef SWIFT_BASIC_UNSAFEPOINTERLIKETYPETRAITS_H
#define SWIFT_BASIC_UNSAFEPOINTERLIKETYPETRAITS_H

#include "llvm/Support/PointerLikeTypeTraits.h"

namespace swift {

template <typename T>
struct UnsafePointerLikeTypeTraits {
  static inline void *getAsVoidPointer(T *P) { return P; }
  static inline T *getFromVoidPointer(void *P) { return P; }

  /// Note, we assume here that void* is related to raw malloc'ed memory and
  /// that malloc returns objects at least 4-byte aligned. However, this may be
  /// wrong, or pointers may be from something other than malloc. In this case,
  /// you should specify a real typed pointer or avoid this template.
  ///
  /// All clients should use assertions to do a run-time check to ensure that
  /// this is actually true.
  enum { NumLowBitsAvailable = 2 };
};

} // end swift namespace

#endif
