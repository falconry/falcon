Falcon
======

<img align="right" style="padding-left: 10px" src="https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Brown-Falcon%2C-Vic%2C-3.1.2008.jpg/160px-Brown-Falcon%2C-Vic%2C-3.1.2008.jpg" alt="falcon picture" />

**[Experimental]**

Falcon is a swift, light-weight framework for building cloud APIs. It tries to do as little as possible while remaining highly effective. 

> Perfection is finally attained not when there is no longer anything to add, but when there is no longer anything to take away. 
>
> *- Antoine de Saint-Exupéry*

### Design ###

**Light-weight.** Only the essentials are included, with few dependencies. We work to keep the code lean-n-mean, making Falcon easier to test, optimize, and deploy. 

**Surprisingly agile.** Although light-weight, Falcon is surprisingly effective. Getting started with the framework is easy. Common web API idioms are supported out of the box without getting in your way. This is a framework designed for journeyman web developers and master craftsman alike.

**Cloud-friendly.** Falcon uses the web-friendly Python language, and speaks WSGI, so you can deploy it on your favorite stack. The framework is designed from the ground up to embrace HTTP, not work against it. Plus, diagnostics are built right in to make it easier to track down sneaky bugs and frustrating performance problems. 

### Assumptions ###

(Work in progress.)

In order to stay lean and fast, Falcon makes several assumptions.

First of all, Falcon assumes that request handlers will (for the most part) do the right thing. In other words, Falcon doesn't try very hard to protect handler code from itself. 

This requires some discipline on the part of the developer.

1. Request handlers will set response variables to sane values. This includes setting *status* to a valid HTTP status code and string (just use the provided constants), setting *headers* to a collection of tuples, and setting *body* (if not desired to be empty) to either a string or an iterable.  
1. The application won't add extra junk to req and resp dicts (use the ctx instead)
1. Request handlers are well-tested with high code coverage. It's not Falcon's job to babysit your code once it leaves the nest.
1. ...

