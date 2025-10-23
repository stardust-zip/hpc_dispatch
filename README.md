# HPC Dispatch Microservice - Frontend Integration Guide

## Overview

The HPC Dispatch Microservice is a FastAPI-based system for managing dispatches (tasks/assignments) and organizing them into hierarchical shelves (folders). This service enables lecturers to create, assign, track, and manage dispatches with full audit history.

**Version:** 1.2.0

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Data Models](#data-models)
- [Common Workflows](#common-workflows)
- [Error Handling](#error-handling)
- [Examples](#examples)

---

## Getting Started

### Base URL

```
http://localhost:8000
```

Or your configured deployment URL.

### CORS Configuration

The service is pre-configured to accept requests from:
- `http://localhost:3000`
- `http://localhost:3001`

If your frontend runs on a different origin, ask the backend team to update `CORS_ORIGINS` in the configuration.

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "ok"
}
```

---

## Authentication

All endpoints (except `/health`, `/`, and `/plug`) require authentication via Bearer token.

### Headers Required

```javascript
{
  "Authorization": "Bearer <your-token>"
}
```

### Authentication Modes

#### 1. Production Mode (Real Authentication)
- Tokens are validated against the HPC User Service
- Use the JWT token from your authentication system

#### 2. Mock Mode (Development)
- Check if mock mode is enabled: `GET /plug`
- Available mock tokens:
  - `lecturer1` (ID: 101, regular lecturer)
  - `lecturer2` (ID: 102, regular lecturer)
  - `lecturer3` (ID: 103, regular lecturer)
  - `admin` (ID: 999, admin lecturer)

Example with mock token:
```javascript
{
  "Authorization": "Bearer lecturer1"
}
```

### User Types & Permissions

- **Lecturers**: Can create dispatches, manage their own drafts, update assigned dispatches
- **Admins**: Full access to all dispatches and system statistics

---

## API Endpoints

### System Endpoints

#### Get Service Info
```
GET /
```

#### Check Authentication Mode
```
GET /plug
```

Response:
```json
{
  "plug_name": "mock_authentication",
  "status": "on",
  "description": "When 'on', auth uses mock users...",
  "available_mock_tokens": ["lecturer1", "lecturer2", "lecturer3", "admin"]
}
```

---

### Dispatch Endpoints

#### 1. Create Dispatch

```
POST /dispatches
```

**Permission:** Lecturers only

**Request Body:**
```json
{
  "title": "Research Paper Review",
  "content": "Please review the attached research paper and provide feedback by next week.",
  "assignee_ids": [102, 103],
  "files": [
    "https://example.com/files/paper.pdf",
    "https://example.com/files/rubric.pdf"
  ]
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "title": "Research Paper Review",
  "content": "Please review the attached...",
  "status": "draft",
  "created_at": "2024-01-15T10:30:00",
  "creator_id": 101,
  "assignee_ids": [102, 103]
}
```

**Notes:**
- New dispatches start in `draft` status
- Must have at least one assignee
- Use `/dispatches/{id}/send` to change status to `pending`

#### 2. Get My Dispatches (List with Filters)

```
GET /dispatches
```

**Query Parameters:**
- `status` (optional): `draft`, `pending`, `in_progress`, `completed`, `rejected`
- `direction` (optional): `incoming` (assigned to me) or `outgoing` (created by me)
- `search` (optional): Search in title and content
- `shelf_id` (optional): Filter by shelf
- `skip` (default: 0): Pagination offset
- `limit` (default: 100): Page size
- `sort_by` (optional): `created_at`, `title`, `status` (default: `created_at`)
- `sort_dir` (optional): `asc`, `desc` (default: `desc`)

**Example Request:**
```
GET /dispatches?direction=incoming&status=pending&limit=20
```

**Response:** `200 OK`
```json
{
  "total": 45,
  "items": [
    {
      "id": 1,
      "title": "Research Paper Review",
      "content": "Please review...",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00",
      "creator_id": 101,
      "assignee_ids": [102, 103]
    }
  ]
}
```

#### 3. Get Dispatch Details

```
GET /dispatches/{dispatch_id}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "title": "Research Paper Review",
  "content": "Please review...",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00",
  "creator_id": 101,
  "assignee_ids": [102, 103],
  "files": [
    {
      "id": 1,
      "file_url": "https://example.com/files/paper.pdf",
      "filename": "paper.pdf",
      "dispatch_id": 1
    }
  ],
  "history": [
    {
      "id": 1,
      "action": "created",
      "details": null,
      "timestamp": "2024-01-15T10:30:00",
      "actor_id": 101,
      "dispatch_id": 1
    },
    {
      "id": 2,
      "action": "sent",
      "details": null,
      "timestamp": "2024-01-15T10:35:00",
      "actor_id": 101,
      "dispatch_id": 1
    }
  ],
  "comments": [
    {
      "id": 1,
      "content": "I have started reviewing this.",
      "created_at": "2024-01-15T11:00:00",
      "user_id": 102,
      "dispatch_id": 1
    }
  ],
  "shelves": []
}
```

#### 4. Update Dispatch

```
PUT /dispatches/{dispatch_id}
```

**Permission:** Creator (draft only) or Admin

**Request Body:**
```json
{
  "title": "Updated Title",
  "content": "Updated content",
  "assignee_ids": [102, 103, 104]
}
```

**Notes:**
- All fields are optional
- Assignees can only be changed on `draft` dispatches (or by admins)

#### 5. Send Dispatch

```
POST /dispatches/{dispatch_id}/send
```

**Permission:** Creator only

**Response:** Changes status from `draft` to `pending`

**Notes:**
- Can only send drafts
- Sends the dispatch to all assigned users

#### 6. Update Dispatch Status

```
PUT /dispatches/{dispatch_id}/status
```

**Permission:** Assignees or Admin

**Request Body:**
```json
{
  "status": "in_progress"
}
```

**Valid Status Values:**
- `pending`
- `in_progress`
- `completed`
- `rejected`

#### 7. Forward Dispatch

```
POST /dispatches/{dispatch_id}/forward
```

**Permission:** Current assignees or Admin

**Request Body:**
```json
{
  "new_assignee_id": 104
}
```

**Notes:**
- Cannot forward `draft` or `completed` dispatches
- Adds the new assignee to existing assignees

#### 8. Add Comment

```
POST /dispatches/{dispatch_id}/comments
```

**Permission:** Creator, Assignees, or Admin

**Request Body:**
```json
{
  "content": "I have completed the review. Please see my notes in the attached file."
}
```

**Response:** `200 OK`
```json
{
  "id": 2,
  "content": "I have completed the review...",
  "created_at": "2024-01-16T14:20:00",
  "user_id": 102,
  "dispatch_id": 1
}
```

#### 9. Delete Dispatch

```
DELETE /dispatches/{dispatch_id}
```

**Permission:** Creator (draft only) or Admin

**Response:** `204 No Content`

---

### Shelf Endpoints

Shelves are hierarchical folders for organizing dispatches.

#### 1. Create Shelf

```
POST /shelves
```

**Request Body:**
```json
{
  "name": "Spring 2024",
  "parent_id": null
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "name": "Spring 2024",
  "user_id": 101,
  "parent_id": null
}
```

#### 2. Get My Shelves (Top-Level)

```
GET /shelves
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Spring 2024",
    "user_id": 101,
    "parent_id": null,
    "children": [
      {
        "id": 2,
        "name": "CS101",
        "user_id": 101,
        "parent_id": 1,
        "children": []
      }
    ]
  }
]
```

#### 3. Get Shelf Details

```
GET /shelves/{shelf_id}
```

**Response:** Returns shelf with nested children and associated dispatches

```json
{
  "id": 2,
  "name": "CS101",
  "user_id": 101,
  "parent_id": 1,
  "children": [],
  "dispatches": [
    {
      "id": 1,
      "title": "Research Paper Review",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00",
      "creator_id": 101,
      "assignee_ids": [102]
    }
  ]
}
```

#### 4. Update Shelf

```
PUT /shelves/{shelf_id}
```

**Request Body:**
```json
{
  "name": "CS101 - Introduction to Programming",
  "parent_id": 1
}
```

#### 5. Delete Shelf

```
DELETE /shelves/{shelf_id}
```

**Notes:**
- Cannot delete a shelf that has child shelves
- Must delete or move children first

#### 6. Add Dispatch to Shelf

```
POST /shelves/{shelf_id}/dispatches/{dispatch_id}
```

**Notes:**
- Can only add dispatches you have access to
- A dispatch can be in multiple shelves

#### 7. Remove Dispatch from Shelf

```
DELETE /shelves/{shelf_id}/dispatches/{dispatch_id}
```

---

### Statistics Endpoints

#### 1. Get My Statistics

```
GET /dispatches/stats/my
```

**Response:** `200 OK`
```json
{
  "incoming": 15,
  "outgoing": 23,
  "status_counts": {
    "draft": 3,
    "pending": 8,
    "in_progress": 12,
    "completed": 14,
    "rejected": 1
  }
}
```

#### 2. Get System Statistics (Admin Only)

```
GET /dispatches/stats/system?limit=5
```

**Response:** `200 OK`
```json
{
  "total_dispatches": 150,
  "status_counts": {
    "draft": 10,
    "pending": 30,
    "in_progress": 45,
    "completed": 60,
    "rejected": 5
  },
  "top_creators": [
    { "user_id": 101, "count": 35 },
    { "user_id": 102, "count": 28 }
  ],
  "top_assignees": [
    { "user_id": 103, "count": 42 },
    { "user_id": 102, "count": 38 }
  ]
}
```

---

### Admin Endpoints

#### Get All Dispatches (Admin Only)

```
GET /admin/dispatches
```

**Query Parameters:**
- `assignee_id` (optional): Filter by assignee
- `creator_id` (optional): Filter by creator
- `status` (optional): Filter by status
- `search` (optional): Search in title/content
- `skip`, `limit`: Pagination

---

## Data Models

### Dispatch Statuses

| Status | Description |
|--------|-------------|
| `draft` | Initial state, not yet sent |
| `pending` | Sent to assignees, awaiting action |
| `in_progress` | Being worked on by assignees |
| `completed` | Work is finished |
| `rejected` | Rejected by assignee |

### Dispatch Actions (History)

- `created` - Dispatch was created
- `modified` - Dispatch was edited
- `sent` - Dispatch was sent (draft → pending)
- `status_updated` - Status changed
- `commented` - Comment was added
- `forwarded` - Dispatch was forwarded to additional assignee

---

## Common Workflows

### Workflow 1: Creating and Sending a Dispatch

```javascript
// 1. Create draft dispatch
const response1 = await fetch('http://localhost:8000/dispatches', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer lecturer1'
  },
  body: JSON.stringify({
    title: 'Grade Assignments',
    content: 'Please grade the midterm assignments by Friday.',
    assignee_ids: [102, 103],
    files: []
  })
});
const dispatch = await response1.json();

// 2. Send the dispatch
await fetch(`http://localhost:8000/dispatches/${dispatch.id}/send`, {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer lecturer1'
  }
});
```

### Workflow 2: Processing an Incoming Dispatch

```javascript
// 1. Get incoming pending dispatches
const response = await fetch('http://localhost:8000/dispatches?direction=incoming&status=pending', {
  headers: {
    'Authorization': 'Bearer lecturer2'
  }
});
const { items } = await response.json();

// 2. Get details of a specific dispatch
const details = await fetch(`http://localhost:8000/dispatches/${items[0].id}`, {
  headers: {
    'Authorization': 'Bearer lecturer2'
  }
});
const dispatch = await details.json();

// 3. Update status to in_progress
await fetch(`http://localhost:8000/dispatches/${dispatch.id}/status`, {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer lecturer2'
  },
  body: JSON.stringify({ status: 'in_progress' })
});

// 4. Add a comment
await fetch(`http://localhost:8000/dispatches/${dispatch.id}/comments`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer lecturer2'
  },
  body: JSON.stringify({
    content: 'I have started working on this.'
  })
});

// 5. Complete the work
await fetch(`http://localhost:8000/dispatches/${dispatch.id}/status`, {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer lecturer2'
  },
  body: JSON.stringify({ status: 'completed' })
});
```

### Workflow 3: Organizing with Shelves

```javascript
// 1. Create a shelf hierarchy
const spring = await fetch('http://localhost:8000/shelves', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer lecturer1'
  },
  body: JSON.stringify({
    name: 'Spring 2024',
    parent_id: null
  })
}).then(r => r.json());

const cs101 = await fetch('http://localhost:8000/shelves', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer lecturer1'
  },
  body: JSON.stringify({
    name: 'CS101',
    parent_id: spring.id
  })
}).then(r => r.json());

// 2. Add dispatch to shelf
await fetch(`http://localhost:8000/shelves/${cs101.id}/dispatches/1`, {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer lecturer1'
  }
});

// 3. Get all dispatches in a shelf
const response = await fetch(`http://localhost:8000/dispatches?shelf_id=${cs101.id}`, {
  headers: {
    'Authorization': 'Bearer lecturer1'
  }
});
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created successfully |
| 204 | Success (no content) |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (invalid/missing token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |
| 503 | Service unavailable (user service down) |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

```javascript
// 401 - Invalid token
{
  "detail": "Could not validate credentials"
}

// 403 - Insufficient permissions
{
  "detail": "Access denied. Only lecturers can perform this action."
}

// 400 - Validation error
{
  "detail": "At least one assignee ID is required."
}

// 404 - Not found
{
  "detail": "Dispatch not found"
}
```

---

## Examples

### React Example with Axios

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
});

// Get my incoming dispatches
export const getIncomingDispatches = async (status = null) => {
  const params = { direction: 'incoming' };
  if (status) params.status = status;
  
  const response = await api.get('/dispatches', { params });
  return response.data;
};

// Create a new dispatch
export const createDispatch = async (dispatchData) => {
  const response = await api.post('/dispatches', dispatchData);
  return response.data;
};

// Send a draft dispatch
export const sendDispatch = async (dispatchId) => {
  const response = await api.post(`/dispatches/${dispatchId}/send`);
  return response.data;
};

// Update dispatch status
export const updateDispatchStatus = async (dispatchId, status) => {
  const response = await api.put(`/dispatches/${dispatchId}/status`, { status });
  return response.data;
};
```

### Vue Example with Fetch

```javascript
// composables/useDispatches.js
import { ref } from 'vue';

export function useDispatches() {
  const dispatches = ref([]);
  const loading = ref(false);
  const error = ref(null);
  
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  };
  
  const fetchDispatches = async (filters = {}) => {
    loading.value = true;
    error.value = null;
    
    try {
      const params = new URLSearchParams(filters);
      const response = await fetch(`http://localhost:8000/dispatches?${params}`, {
        headers: { 'Authorization': headers.Authorization }
      });
      
      if (!response.ok) {
        throw new Error(await response.text());
      }
      
      const data = await response.json();
      dispatches.value = data.items;
      return data;
    } catch (e) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };
  
  const createDispatch = async (dispatchData) => {
    const response = await fetch('http://localhost:8000/dispatches', {
      method: 'POST',
      headers,
      body: JSON.stringify(dispatchData)
    });
    
    if (!response.ok) {
      throw new Error(await response.text());
    }
    
    return response.json();
  };
  
  return {
    dispatches,
    loading,
    error,
    fetchDispatches,
    createDispatch
  };
}
```

### Angular Example with HttpClient

```typescript
// services/dispatch.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

interface PaginatedResponse<T> {
  total: number;
  items: T[];
}

interface Dispatch {
  id: number;
  title: string;
  content: string;
  status: string;
  created_at: string;
  creator_id: number;
  assignee_ids: number[];
}

@Injectable({
  providedIn: 'root'
})
export class DispatchService {
  private baseUrl = 'http://localhost:8000';
  
  constructor(private http: HttpClient) {}
  
  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }
  
  getDispatches(filters?: {
    direction?: string;
    status?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }): Observable<PaginatedResponse<Dispatch>> {
    let params = new HttpParams();
    if (filters) {
      Object.keys(filters).forEach(key => {
        if (filters[key]) {
          params = params.set(key, filters[key]);
        }
      });
    }
    
    return this.http.get<PaginatedResponse<Dispatch>>(
      `${this.baseUrl}/dispatches`,
      { headers: this.getHeaders(), params }
    );
  }
  
  createDispatch(dispatch: any): Observable<Dispatch> {
    return this.http.post<Dispatch>(
      `${this.baseUrl}/dispatches`,
      dispatch,
      { headers: this.getHeaders() }
    );
  }
  
  updateStatus(dispatchId: number, status: string): Observable<Dispatch> {
    return this.http.put<Dispatch>(
      `${this.baseUrl}/dispatches/${dispatchId}/status`,
      { status },
      { headers: this.getHeaders() }
    );
  }
}
```

---

## Interactive API Documentation

Once the service is running, you can access interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide a complete reference with the ability to test endpoints directly from your browser.

---

## Support

For questions or issues:
1. Check the interactive API docs at `/docs`
2. Verify authentication mode with `GET /plug`
3. Contact the backend team with error details and request/response examples

---

**Last Updated:** 2024
**Service Version:** 1.2.0