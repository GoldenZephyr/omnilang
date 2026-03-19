#program base.


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Establish initial state
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

holds(Variable, Value, 0) :- initialState(Variable, Value).

satisfied(DerivedPredicate, type(and), 0) :- derivedPredicate(DerivedPredicate, type(and)), holds(Variable, Value, 0) : precondition(DerivedPredicate, type(and), Variable, Value).
satisfied(DerivedPredicate, type(or), 0) :- precondition(DerivedPredicate, type(or), Variable, Value), holds(Variable, Value, 0).

holds(DerivedVariable, Value, 0) :- satisfied(DerivedPredicate, Type, 0), postcondition(DerivedPredicate, Type, effect(unconditional), DerivedVariable, Value).
holds(DerivedVariable, value(DerivedVariable, false), 0) :- derivedVariable(DerivedVariable), not holds(DerivedVariable, value(DerivedVariable, true), 0).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Compute derived predicates
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#program step(t).
time(t).

% conjunctive preconditions
satisfied(DerivedPredicate, type(and), t) :- derivedPredicate(DerivedPredicate, type(and)), holds(Variable, Value, t) : precondition(DerivedPredicate, type(and), Variable, Value).

% disjunctive preconditions
satisfied(DerivedPredicate, type(or), t) :- precondition(DerivedPredicate, type(or), Variable, Value), holds(Variable, Value, t).

holds(DerivedVariable, Value, t) :- satisfied(DerivedPredicate, Type, t), postcondition(DerivedPredicate, Type, effect(unconditional), DerivedVariable, Value).

holds(DerivedVariable, value(DerivedVariable, false), t) :- derivedVariable(DerivedVariable), not holds(DerivedVariable, value(DerivedVariable, true), t).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Perform actions
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


#show action/1.
1 {occurs(Action, t) : action(Action)} 1.

% Check preconditions
:- occurs(Action, t), precondition(Action, Variable, Value), not holds(Variable, Value, t - 1).

% Apply effects
caused(Variable, Value, t) :-
	occurs(Action, t),
	postcondition(Action, Effect, Variable, Value),
	holds(VariablePre, ValuePre, t - 1) : precondition(Effect, VariablePre, ValuePre).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Inertia rules
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

modified(Variable, t) :- caused(Variable, Value, t).

holds(Variable, Value, t) :- caused(Variable, Value, t).
holds(variable(V), Value, t) :- holds(variable(V), Value, t - 1), not modified(variable(V), t).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Variables and mutex groups
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Check that variables have unique values
:- variable(Variable), not 1 {holds(Variable, Value, t) : contains(Variable, Value)} 1.

% Check mutexes
:- mutexGroup(MutexGroup), not {holds(Variable, Value, t) : contains(MutexGroup, Variable, Value)} 1.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Verify that goal is met
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#program check(t).
:- goal(Variable, Value), not holds(Variable, Value, t).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#show occurs/2.
% #show satisfied/3.
% #show holds(derivedVariable("derived-predicate-1"), V, H) : holds(derivedVariable("derived-predicate-1"), V, H).
%print(V,H) :-
%    holds(derivedVariable("derived-predicate-1"), V, H).
% #show print/2.
%printbad(V,H) :-
%    holds(derivedVariable(derivedVariable("derived-predicate-1")), V, H).
% #show printbad/2.
% #show holds/3.


% #show isholding(X1, V, T) : holds(variable(variable(("holding", X1))), V, T).
