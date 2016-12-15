" Copyright 2016 Google Inc. All rights reserved.
"
" Licensed under the Apache License, Version 2.0 (the "License");
" you may not use this file except in compliance with the License.
" You may obtain a copy of the License at
"
"     http://www.apache.org/licenses/LICENSE-2.0
"
" Unless required by applicable law or agreed to in writing, software
" distributed under the License is distributed on an "AS IS" BASIS,
" WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
" See the License for the specific language governing permissions and
" limitations under the License.

" Vim syntax file
" Language: Sprockets STL
" Maintainer: mbjorge@google.com

if exists("b:current_syntax")
  finish
endif

"--------------
" STL comments
"--------------
syn keyword stlTodo contained TODO
syn match stlComment '//.*$' contains=stlTodo

"--------------------
" STL reserved words
"--------------------
syn keyword stlReservedWordsTypes const bool int string
syn keyword stlReservedWords encode error_states event events message
syn keyword stlReservedWords module optional post_states pre_states qualifier
syn keyword stlReservedWords repeated required role state transition

"---------------
" STL externals
"---------------
syn region stlExternalString start='"'hs=s+1 end='"'he=e-1 contained
syn keyword stlReservedWords external nextgroup=stlExternalString skipwhite

"-------------
" STL symbols
"-------------
syn match stlArrow '->'

"---------------------
" STL constant values
"---------------------
syn keyword stlBool true false

syn match stlInt '[-]\d+'
syn match stlInt '\d+'

syn region stlString start='"' skip='\\"' end='"'


"------------------------
" Set the current syntax
"------------------------
let b:current_syntax = 'stl'

"------------------------
" STL highlighting rules
"------------------------
hi def link stlTodo Todo
hi def link stlComment Comment
hi def link stlReservedWords Keyword
hi def link stlReservedWordsTypes Type
hi def link stlArrow Operator
hi def link stlBoolean Boolean
hi def link stlInt Number
hi def link stlString String
hi def link stlExternalString Underlined
