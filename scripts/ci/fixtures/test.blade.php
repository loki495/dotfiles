{{-- A Blade comment --}}
<div class="card" x-data="{ open: true }">
    @if ($user)
        <h1>{{ $user->name }}</h1>
        {!! $content !!}
    @else
        <p>No user</p>
    @endif
    @foreach ($items as $item)
        <span>{{ $item }}</span>
    @endforeach
    @php
        $count = count($items);
    @endphp
</div>
<script>const message = `Hello ${name}`;</script>
<style>.card { color: red; }</style>
