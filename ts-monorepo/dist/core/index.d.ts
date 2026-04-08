import { z } from 'zod';

declare const configSchema: z.ZodObject<{
    jira_server: z.ZodString;
    jira_token: z.ZodString;
    "project-id": z.ZodOptional<z.ZodString>;
    "parent-key": z.ZodOptional<z.ZodString>;
    "rank-by": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    order: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    "status-order": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    "issuetype-order": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    "epic-order": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    components_to_track: z.ZodOptional<z.ZodString>;
    default_reporter: z.ZodOptional<z.ZodString>;
    default_assignee: z.ZodOptional<z.ZodString>;
    default_component: z.ZodOptional<z.ZodString>;
    default_customfield_10247: z.ZodOptional<z.ZodString>;
    epic_link_field_id: z.ZodOptional<z.ZodString>;
    sprint: z.ZodOptional<z.ZodString>;
}, "passthrough", z.ZodTypeAny, z.objectOutputType<{
    jira_server: z.ZodString;
    jira_token: z.ZodString;
    "project-id": z.ZodOptional<z.ZodString>;
    "parent-key": z.ZodOptional<z.ZodString>;
    "rank-by": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    order: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    "status-order": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    "issuetype-order": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    "epic-order": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    components_to_track: z.ZodOptional<z.ZodString>;
    default_reporter: z.ZodOptional<z.ZodString>;
    default_assignee: z.ZodOptional<z.ZodString>;
    default_component: z.ZodOptional<z.ZodString>;
    default_customfield_10247: z.ZodOptional<z.ZodString>;
    epic_link_field_id: z.ZodOptional<z.ZodString>;
    sprint: z.ZodOptional<z.ZodString>;
}, z.ZodTypeAny, "passthrough">, z.objectInputType<{
    jira_server: z.ZodString;
    jira_token: z.ZodString;
    "project-id": z.ZodOptional<z.ZodString>;
    "parent-key": z.ZodOptional<z.ZodString>;
    "rank-by": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    order: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    "status-order": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    "issuetype-order": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    "epic-order": z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    components_to_track: z.ZodOptional<z.ZodString>;
    default_reporter: z.ZodOptional<z.ZodString>;
    default_assignee: z.ZodOptional<z.ZodString>;
    default_component: z.ZodOptional<z.ZodString>;
    default_customfield_10247: z.ZodOptional<z.ZodString>;
    epic_link_field_id: z.ZodOptional<z.ZodString>;
    sprint: z.ZodOptional<z.ZodString>;
}, z.ZodTypeAny, "passthrough">>;
type JiraConfig = z.infer<typeof configSchema>;
declare function loadConfig(path: string): Promise<JiraConfig>;

interface JiraRequestOptions extends RequestInit {
    path: string;
    searchParams?: Record<string, string | number | boolean | undefined>;
}
interface JiraResponse<T> {
    ok: boolean;
    status: number;
    data: T | null;
    error?: unknown;
}
declare function jiraRequest<T = unknown>(config: JiraConfig, options: JiraRequestOptions): Promise<JiraResponse<T>>;

interface CsvParseOptions<T> {
    header?: boolean;
    transform?: (row: Record<string, string>) => T;
}
declare function parseCsv<T = Record<string, string>>(content: string, options?: CsvParseOptions<T>): T[];

type LogLevel = "debug" | "info" | "warn" | "error";
interface Logger {
    debug: (...args: unknown[]) => void;
    info: (...args: unknown[]) => void;
    warn: (...args: unknown[]) => void;
    error: (...args: unknown[]) => void;
}
declare function createLogger(level?: LogLevel): Logger;

interface CreateIssueResponse {
    id: string;
    key: string;
    self: string;
}
interface JiraIssueCreateFields {
    project: {
        key: string;
    };
    summary: string;
    description?: string;
    issuetype: {
        name: string;
    };
    reporter?: {
        name: string;
    };
    assignee?: {
        name: string;
    };
    parent?: {
        key: string;
    };
    components?: Array<{
        name: string;
    }>;
    [customField: string]: unknown;
}
interface JiraIssueUpdateFields {
    assignee?: {
        name: string;
    };
    [customField: string]: unknown;
}
interface JiraIssue {
    key: string;
    id: string;
    fields: Record<string, unknown>;
}
declare class JiraClient {
    private readonly config;
    constructor(config: JiraConfig);
    createIssue(fields: JiraIssueCreateFields): Promise<CreateIssueResponse>;
    updateIssue(issueKey: string, fields: JiraIssueUpdateFields): Promise<void>;
    deleteIssue(issueKey: string): Promise<void>;
    searchIssues<TFields = unknown>(jql: string, fields?: string[]): Promise<Array<JiraIssue & {
        fields: TFields;
    }>>;
}

interface ImportRow {
    [key: string]: string | undefined;
    "Issue ID"?: string;
    "Parent ID"?: string;
    "Summary"?: string;
    "Description"?: string;
    "Issue Type"?: string;
    "Reporter"?: string;
    "Assignee"?: string;
    "Epic Link"?: string;
}
interface LogEntry {
    issueKey: string;
    action: "C" | "U" | "D";
    payload: Record<string, unknown>;
}
interface BatchProcessorOptions {
    logger?: {
        info: (...args: unknown[]) => void;
        warn: (...args: unknown[]) => void;
        error: (...args: unknown[]) => void;
    };
}
declare class BatchProcessor {
    private readonly config;
    private client;
    constructor(config: JiraConfig, options?: BatchProcessorOptions);
    private logger;
    createIssues(rows: ImportRow[]): Promise<LogEntry[]>;
    deleteIssues(rows: ImportRow[]): Promise<LogEntry[]>;
    updateIssues(rows: ImportRow[]): Promise<LogEntry[]>;
    private createIssue;
}

interface RankOptions {
    rankBy: string[];
    order?: string[];
    statusOrder?: string[];
    issuetypeOrder?: string[];
    epicOrder?: string[];
    dryRun?: boolean;
    brief?: boolean;
}
interface RankResult {
    analyzed: number;
    moved: number;
}
declare class RankingService {
    private readonly config;
    private client;
    constructor(config: JiraConfig);
    rankChildren(parentKey: string, options: RankOptions): Promise<RankResult>;
    rankProjectEpics(projectKey: string, options: RankOptions): Promise<RankResult>;
    rankCollection(label: string, issues: unknown[], options: RankOptions): Promise<RankResult>;
}

export { BatchProcessor, type BatchProcessorOptions, type CreateIssueResponse, type CsvParseOptions, type ImportRow, JiraClient, type JiraConfig, type JiraIssue, type JiraIssueCreateFields, type JiraIssueUpdateFields, type JiraRequestOptions, type JiraResponse, type LogEntry, type LogLevel, type Logger, type RankOptions, type RankResult, RankingService, createLogger, jiraRequest, loadConfig, parseCsv };
