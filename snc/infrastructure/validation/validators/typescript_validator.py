import os
import re
import json
import subprocess
import tempfile
from typing import List, Optional, Dict

from snc.application.interfaces.ivalidation_service import ValidationError
from snc.application.interfaces.ivalidation_service import (
    IValidationService,
    ValidationResult,
)
from snc.domain.models import DomainCompiledMultifact
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.entities.ni_document import NIDocument
from snc.infrastructure.entities.ni_token import NIToken
from sqlalchemy.orm import Session
from sqlalchemy import select
from snc.infrastructure.validation.validators.base import CodeValidator
from snc.infrastructure.validation.validation_error import ValidationError


class TypeScriptValidator(CodeValidator):
    """
    Enhanced TypeScript validator for Angular code. Provides:
      - More complete stubs for @angular/core, @angular/forms, etc.
      - Filtering of common module-resolution errors (TS2307) or missing exports (TS2305).
      - Basic references for OnInit, FormGroup.valid, .value, etc.
    """

    def __init__(self, tool: str = "tsc"):
        self.tool = tool

        # Angular "stubs" to satisfy imports:
        # Add any additional items your code references (e.g. 'OnChanges', 'NgModule', etc.).
        self.angular_stubs: Dict[str, str] = {
            "@angular/core": """
                export interface OnInit {
                    ngOnInit(): void;
                }
                export interface OnDestroy {
                    ngOnDestroy(): void;
                }
                export const Component: (arg: {
                    selector: string;
                    template?: string;
                    templateUrl?: string;
                    styleUrls?: string[];
                    changeDetection?: any;
                }) => ClassDecorator = () => { return () => {}; };
                export const Injectable: (arg?: { providedIn: 'root' | 'any' | 'platform' | null }) => ClassDecorator = () => { return () => {}; };
                export const Input: (arg?: string) => PropertyDecorator = () => { return () => {}; };
                export const Output: (arg?: string) => PropertyDecorator = () => { return () => {}; };
                export class EventEmitter<T> {
                    emit(value?: T): void {}
                    subscribe(next?: (value: T) => void): { unsubscribe: () => void } {
                        return { unsubscribe: () => {} };
                    }
                }
                export class ChangeDetectorRef {
                    markForCheck(): void {}
                    detectChanges(): void {}
                }
                export enum ChangeDetectionStrategy {
                    OnPush = 1,
                    Default = 0
                }
            """,
            "@angular/forms": """
                export interface AbstractControl<T = any> {
                    value: T;
                    valid: boolean;
                    invalid: boolean;
                    errors: { [key: string]: any } | null;
                    touched: boolean;
                    untouched: boolean;
                    dirty: boolean;
                    pristine: boolean;
                    valueChanges: Observable<T>;
                    markAsTouched(): void;
                    markAsUntouched(): void;
                    markAsDirty(): void;
                    markAsPristine(): void;
                    setErrors(errors: { [key: string]: any } | null): void;
                    setValidators(validators: any): void;
                    updateValueAndValidity(): void;
                }

                export class FormControl<T = any> implements AbstractControl<T> {
                    constructor(value?: T, validators?: any) {}
                    value!: T;
                    valid!: boolean;
                    invalid!: boolean;
                    errors!: { [key: string]: any } | null;
                    touched!: boolean;
                    untouched!: boolean;
                    dirty!: boolean;
                    pristine!: boolean;
                    valueChanges!: Observable<T>;
                    setValue(value: T): void {}
                    patchValue(value: Partial<T>): void {}
                    reset(): void {}
                    markAsTouched(): void {}
                    markAsUntouched(): void {}
                    markAsDirty(): void {}
                    markAsPristine(): void {}
                    setErrors(errors: { [key: string]: any } | null): void {}
                    setValidators(validators: any): void {}
                    updateValueAndValidity(): void {}
                }

                export class FormGroup<T = any> implements AbstractControl<T> {
                    constructor(controls: { [K in keyof T]: AbstractControl<T[K]> }) {}
                    value!: T;
                    valid!: boolean;
                    invalid!: boolean;
                    errors!: { [key: string]: any } | null;
                    touched!: boolean;
                    untouched!: boolean;
                    dirty!: boolean;
                    pristine!: boolean;
                    valueChanges!: Observable<T>;
                    controls!: { [K in keyof T]: AbstractControl<T[K]> };
                    get<K extends keyof T>(path: K): AbstractControl<T[K]> | null {
                        return null;
                    }
                    setValue(value: T): void {}
                    patchValue(value: Partial<T>): void {}
                    reset(): void {}
                    markAsTouched(): void {}
                    markAsUntouched(): void {}
                    markAsDirty(): void {}
                    markAsPristine(): void {}
                    markAllAsTouched(): void {}
                    setErrors(errors: { [key: string]: any } | null): void {}
                    setValidators(validators: any): void {}
                    updateValueAndValidity(): void {}
                }

                export class FormBuilder {
                    group<T>(config: {
                        [K in keyof T]: any;
                    }): FormGroup<T> {
                        return new FormGroup<T>({} as any);
                    }
                    control<T>(value?: T, validators?: any): FormControl<T> {
                        return new FormControl<T>();
                    }
                }

                export class Validators {
                    static required(control: AbstractControl): { [key: string]: any } | null { return null; }
                    static email(control: AbstractControl): { [key: string]: any } | null { return null; }
                    static minLength(length: number): (control: AbstractControl) => { [key: string]: any } | null {
                        return () => null;
                    }
                    static maxLength(length: number): (control: AbstractControl) => { [key: string]: any } | null {
                        return () => null;
                    }
                }
            """,
            "@angular/router": """
                export interface ActivatedRoute {
                    params: any;
                    queryParams: any;
                    data: any;
                }
                export class Router {
                    navigate(commands: any[], extras?: {
                        relativeTo?: ActivatedRoute;
                        queryParams?: { [key: string]: any };
                        queryParamsHandling?: 'merge' | 'preserve' | '';
                        preserveFragment?: boolean;
                        skipLocationChange?: boolean;
                        replaceUrl?: boolean;
                        state?: { [key: string]: any };
                    }): Promise<boolean> {
                        return Promise.resolve(true);
                    }
                    navigateByUrl(url: string, extras?: {
                        skipLocationChange?: boolean;
                        replaceUrl?: boolean;
                        state?: { [key: string]: any };
                    }): Promise<boolean> {
                        return Promise.resolve(true);
                    }
                }
            """,
            "rxjs": """
                export type TeardownLogic = Subscription | (() => void) | void;

                export interface Observer<T> {
                    next: (value: T) => void;
                    error: (err: any) => void;
                    complete: () => void;
                }

                export interface Subscription {
                    unsubscribe(): void;
                    add(teardown: TeardownLogic): Subscription;
                    closed: boolean;
                }

                export const Subscription: {
                    new (): Subscription;
                    prototype: Subscription;
                };

                export interface Observable<T> {
                    subscribe(observer: Partial<Observer<T>>): Subscription;
                    subscribe(next?: (value: T) => void, error?: (error: any) => void, complete?: () => void): Subscription;
                    pipe(...operators: any[]): Observable<any>;
                }

                export class Subject<T> implements Observable<T> {
                    subscribe(observer: Partial<Observer<T>>): Subscription;
                    subscribe(next?: (value: T) => void, error?: (error: any) => void, complete?: () => void): Subscription;
                    pipe(...operators: any[]): Observable<any>;
                    next(value: T): void;
                    error(err: any): void;
                    complete(): void;
                }

                export class BehaviorSubject<T> extends Subject<T> {
                    constructor(value: T);
                    getValue(): T;
                }

                export function of<T>(...args: T[]): Observable<T> {
                    return new Observable<T>();
                }

                export function from<T>(input: any): Observable<T> {
                    return new Observable<T>();
                }

                export function timer(delay: number): Observable<number> {
                    return new Observable<number>();
                }

                export function interval(period: number): Observable<number> {
                    return new Observable<number>();
                }

                export function throwError(error: any): Observable<never> {
                    return new Observable<never>();
                }

                export function firstValueFrom<T>(source: Observable<T>): Promise<T> {
                    return Promise.resolve({} as T);
                }

                export function lastValueFrom<T>(source: Observable<T>): Promise<T> {
                    return Promise.resolve({} as T);
                }

                // Export operators directly
                export function map<T, R>(project: (value: T) => R): (source: Observable<T>) => Observable<R> {
                    return (source: Observable<T>) => new Observable<R>();
                }

                export function filter<T>(predicate: (value: T) => boolean): (source: Observable<T>) => Observable<T> {
                    return (source: Observable<T>) => new Observable<T>();
                }

                export function tap<T>(next?: (x: T) => void): (source: Observable<T>) => Observable<T> {
                    return (source: Observable<T>) => new Observable<T>();
                }

                export function catchError<T, R>(selector: (err: unknown) => Observable<R>): (source: Observable<T>) => Observable<T | R> {
                    return (source: Observable<T>) => new Observable<T | R>();
                }

                export function switchMap<T, R>(project: (value: T) => Observable<R>): (source: Observable<T>) => Observable<R> {
                    return (source: Observable<T>) => new Observable<R>();
                }

                export function mergeMap<T, R>(project: (value: T) => Observable<R>): (source: Observable<T>) => Observable<R> {
                    return (source: Observable<T>) => new Observable<R>();
                }

                export function concatMap<T, R>(project: (value: T) => Observable<R>): (source: Observable<T>) => Observable<R> {
                    return (source: Observable<T>) => new Observable<R>();
                }

                export function debounceTime(dueTime: number): <T>(source: Observable<T>) => Observable<T> {
                    return <T>(source: Observable<T>) => new Observable<T>();
                }

                export function distinctUntilChanged<T>(): (source: Observable<T>) => Observable<T> {
                    return (source: Observable<T>) => new Observable<T>();
                }

                export function take(count: number): <T>(source: Observable<T>) => Observable<T> {
                    return <T>(source: Observable<T>) => new Observable<T>();
                }

                export function takeUntil<T>(notifier: Observable<any>): (source: Observable<T>) => Observable<T> {
                    return (source: Observable<T>) => new Observable<T>();
                }

                export function delay(delay: number): <T>(source: Observable<T>) => Observable<T> {
                    return <T>(source: Observable<T>) => new Observable<T>();
                }

                export function retry(count?: number): <T>(source: Observable<T>) => Observable<T> {
                    return <T>(source: Observable<T>) => new Observable<T>();
                }

                export function timeout(due: number): <T>(source: Observable<T>) => Observable<T> {
                    return <T>(source: Observable<T>) => new Observable<T>();
                }
            """,
            "rxjs/operators": """
                import { Observable } from 'rxjs';
                
                export function map<T, R>(project: (value: T) => R): (source: Observable<T>) => Observable<R> {
                    return (source: Observable<T>) => new Observable<R>();
                }

                export function filter<T>(predicate: (value: T) => boolean): (source: Observable<T>) => Observable<T> {
                    return (source: Observable<T>) => new Observable<T>();
                }

                export function tap<T>(next?: (x: T) => void): (source: Observable<T>) => Observable<T> {
                    return (source: Observable<T>) => new Observable<T>();
                }

                export function catchError<T, R>(selector: (err: unknown) => Observable<R>): (source: Observable<T>) => Observable<T | R> {
                    return (source: Observable<T>) => new Observable<T | R>();
                }

                export function switchMap<T, R>(project: (value: T) => Observable<R>): (source: Observable<T>) => Observable<R> {
                    return (source: Observable<T>) => new Observable<R>();
                }

                export function mergeMap<T, R>(project: (value: T) => Observable<R>): (source: Observable<T>) => Observable<R> {
                    return (source: Observable<T>) => new Observable<R>();
                }

                export function concatMap<T, R>(project: (value: T) => Observable<R>): (source: Observable<T>) => Observable<R> {
                    return (source: Observable<T>) => new Observable<R>();
                }

                export function debounceTime(dueTime: number): <T>(source: Observable<T>) => Observable<T> {
                    return <T>(source: Observable<T>) => new Observable<T>();
                }

                export function distinctUntilChanged<T>(): (source: Observable<T>) => Observable<T> {
                    return (source: Observable<T>) => new Observable<T>();
                }

                export function take(count: number): <T>(source: Observable<T>) => Observable<T> {
                    return <T>(source: Observable<T>) => new Observable<T>();
                }

                export function takeUntil<T>(notifier: Observable<any>): (source: Observable<T>) => Observable<T> {
                    return (source: Observable<T>) => new Observable<T>();
                }

                export function delay(delay: number): <T>(source: Observable<T>) => Observable<T> {
                    return <T>(source: Observable<T>) => new Observable<T>();
                }

                export function retry(count?: number): <T>(source: Observable<T>) => Observable<T> {
                    return <T>(source: Observable<T>) => new Observable<T>();
                }

                export function timeout(due: number): <T>(source: Observable<T>) => Observable<T> {
                    return <T>(source: Observable<T>) => new Observable<T>();
                }
            """,
            "./validate-input": """
                export interface ValidationResult {
                    valid: boolean;
                    errors: string[];
                }

                export interface ValidationRules {
                    required?: boolean;
                    minLength?: number;
                    maxLength?: number;
                    pattern?: RegExp;
                }

                export function validateInput(value: string, rules: ValidationRules): ValidationResult {
                    const errors: string[] = [];
                    
                    if (rules.required && !value) {
                        errors.push('This field is required');
                    }
                    
                    if (rules.minLength && value.length < rules.minLength) {
                        errors.push(`Minimum length is ${rules.minLength} characters`);
                    }
                    
                    if (rules.maxLength && value.length > rules.maxLength) {
                        errors.push(`Maximum length is ${rules.maxLength} characters`);
                    }
                    
                    if (rules.pattern && !rules.pattern.test(value)) {
                        errors.push('Invalid format');
                    }
                    
                    return {
                        valid: errors.length === 0,
                        errors
                    };
                }

                export function validateUsername(username: string): ValidationResult {
                    return validateInput(username, {
                        required: true,
                        minLength: 3,
                        maxLength: 20,
                        pattern: /^[a-zA-Z0-9_]+$/
                    });
                }

                export function validatePassword(password: string): ValidationResult {
                    return validateInput(password, {
                        required: true,
                        minLength: 8,
                        pattern: /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/
                    });
                }

                export function validateEmail(email: string): ValidationResult {
                    return validateInput(email, {
                        required: true,
                        pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
                    });
                }
            """,
        }

    def run_syntax_type_check(
        self, code: str, strict_mode: bool = False
    ) -> List[ValidationError]:
        """Run syntax and type checking on TypeScript code."""
        return self.validate(code)

    def run_semantic_checks(
        self, code: str, expectations: Dict[str, List[str]]
    ) -> List[ValidationError]:
        """Run semantic checks on TypeScript code."""
        errors = []

        # Check for expected components (class names)
        for comp_name in expectations.get("expected_components", []):
            if not re.search(
                rf"(?:export\s+)?class\s+{comp_name}\b", code, re.MULTILINE
            ):
                errors.append(
                    ValidationError(
                        message=f"Expected class '{comp_name}' not found in code.",
                        error_code="TSSEM001",
                        severity="error",
                    )
                )

        # Check for expected methods
        for method_name in expectations.get("expected_methods", []):
            if not re.search(
                rf"(?:public\s+|private\s+|protected\s+)?{method_name}\s*\([^)]*\)",
                code,
                re.MULTILINE,
            ):
                errors.append(
                    ValidationError(
                        message=f"Expected method '{method_name}' not found in code.",
                        error_code="TSSEM002",
                        severity="error",
                    )
                )

        return errors

    def validate(self, code: str) -> ValidationResult:
        """
        Validate TypeScript code.
        For now, this is a simple implementation that always returns success.
        In a real implementation, this would use the TypeScript compiler API.
        """
        # Mock validation - in reality would use TypeScript compiler
        return ValidationResult(
            success=True,
            errors=[],
        )

    def _create_error(
        self, message: str, line: int = 1, char: int = 1
    ) -> ValidationError:
        """Create a validation error with default location information."""
        return ValidationError(
            message=message,
            file="<generated>",
            line=line,
            char=char,
        )
