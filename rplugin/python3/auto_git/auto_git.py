from os import sync
from git.index.base import Treeish
import neovim
import subprocess
from pynvim import Nvim

from git.repo import Repo

from auto_git.Git import Git


@neovim.plugin
class AutoGit(object):
    def __init__(self, vim: Nvim):
        self.vim = vim 
        self.git = Git()
        self.buffer_status = """
help

branchs : 1
add : a
restore form staging : r
commit : c
push : p
pull : u
exit : q

Current branch = {}

Untracked files
{}

Staging files
{}
"""
        self.buffer_branch="""
help

git status : 1
switch : i
merge : m
delete branch : d
make branch : a
exit : q

Current branch = {}

Branchs

{}
"""

        self.start_line_branch = 13
        self.start_line_status= 13

    def window(self,buf) -> None:
        width = 100 
        height = 30 

        win = self.vim.api.open_win(buf, True, {
            'relative': 'win',
            'width': width,
            'height': height,
            'col': int((self.vim.current.window.width - width) / 2),
            'row': int((self.vim.current.window.height - height) / 2),
            'border': 'rounded',
            'style': 'minimal',
        })

        

        # Prevent editing in the buffer
        self.vim.command('setlocal nomodifiable')
        


    @neovim.command('AutoGit', nargs='*', range='', sync=True)
    def auto_git(self, args, range):
        # Run git status command
        untracked_files, staging_files= self.git.status() 
        current_branch = self.git.current_branch() 
        staging_files = [item.a_path for item in staging_files]
        content = self.buffer_status.format(current_branch, '\n'.join(untracked_files), '\n'.join(staging_files)).strip().splitlines()

        buf = self.vim.api.create_buf(False, True)

        self.vim.api.buf_set_lines(buf, 0, -1, False, content)

        self.window(buf)
        self.update(0)
        
        # Jump to the first line of files
        self.vim.command(':15')

        # Map 'a' key to return the current line content and perform git add
        self.vim.command("nnoremap <buffer> a :call AutoGitModify()<CR>")
        self.vim.command("nnoremap <buffer> c :call AutoGitCommit()<CR>")
        self.vim.command("nnoremap <buffer> p :call AutoGitPush()<CR>")  
        self.vim.command("nnoremap <buffer> u :call AutoGitPull()<CR>")
        self.vim.command("nnoremap <buffer> q :q! <CR>")
        self.vim.command("nnoremap <buffer> 1 :call AutoGitpanel(2) <CR>")

    @neovim.command('AutoGitBranch', nargs='*', range='')
    def branchs(self, args, range):
     
        result = subprocess.run(['git', 'branch','-a'], capture_output=True, text=True)
        current_branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True)
        result.stdout = result.stdout.replace('*',' ')
        
        width = 100 
        height = 80 
        content = self.buffer_branch.format(current_branch.stdout.strip(), result.stdout).strip().splitlines()

        buf = self.vim.api.create_buf(False, True)
        self.vim.api.buf_set_lines(buf, 0, -1, False, content)

        win = self.vim.api.open_win(buf, True, {
            'relative': 'editor',
            'width': width,
            'height': height,
            'col': int((self.vim.current.window.width - width) / 2),
            'row': int((self.vim.current.window.height - height) / 2),
            'border': 'rounded',
            'style': 'minimal',
        })

        

        # Prevent editing in the buffer
        self.vim.command('setlocal nomodifiable')


        # Jump to the first line of branch 
        self.vim.command(':14')
        
        self.vim.command("nnoremap <buffer> q :q! <CR>")
        self.vim.command("nnoremap <buffer> i :call AutoGitSwitch() <CR>")
        self.vim.command("nnoremap <buffer> a :call AutoGitMakeBranch() <CR>")
        self.vim.command("nnoremap <buffer> d :call AutoGitDeleteBranch() <CR>")
        self.vim.command("nnoremap <buffer> m :call AutoGitMerge() <CR>")
        self.vim.command("nnoremap <buffer> 1 :call AutoGitpanel(1) <CR>")


    @neovim.function('AutoGitpanel', sync=True)
    def switch_panels(self, args):
       self.vim.command(":q!")
       if args == [1] :
           self.vim.command(":AutoGit")
           return
       if args == [2] :
           self.vim.command(":AutoGitBranch")
           return
            
    @neovim.function('AutoGitMerge')
    def merge(self, args):
        line_number = self.vim.current.window.cursor[0]
        if line_number < self.start_line_branch:
            self.vim.command('echo "Invalid select "')
            return
        line_content = self.vim.current.buffer[line_number - 1][2:]
        
        if line_content[:15] == 'remotes/origin/':
            self.vim.command('echo "Invalid select "')
            return
        
        result = subprocess.run(['git', 'merge',line_content], capture_output=True, text=True)
        if len(result.stderr) > 0:
            self.vim.command('echo "{}"'.format(result.stderr))
        else:
            self.vim.command('echo "Branch was merged"')
        self.update(1)

    @neovim.function('AutoGitDeleteBranch')
    def delete_branch(self, args):
        line_number = self.vim.current.window.cursor[0]
        if line_number < self.start_line_branch:
            self.vim.command('echo "Invalid select "')
            return
        line_content = self.vim.current.buffer[line_number - 1][2:]

        if line_content[:15] == 'remotes/origin/':
            result = subprocess.run(['git', 'push','origin','--delete', line_content[15:]], capture_output=True, text=True)
            if len(result.stderr) > 0:
                self.vim.command('echo "{}"'.format(result.stderr))
            else:
                self.vim.command('echo "{}"'.format(result.stdout))
            self.update(1)
            return

        result = subprocess.run(['git', 'branch','-D', line_content], capture_output=True, text=True)
        if len(result.stderr) > 0:
            self.vim.command('echo "{}"'.format(result.stderr))
        else:
            self.vim.command('echo "{}"'.format(result.stdout))
        self.update(1)
        
       
    @neovim.function('AutoGitSwitch')
    def switch(self, args):
        line_number = self.vim.current.window.cursor[0]
        if line_number < self.start_line_branch:
            self.vim.command('echo "Invalid select "')
            return
        line_content = self.vim.current.buffer[line_number - 1][2:]

        if line_content[:15] == 'remotes/origin/':
            self.vim.command('echo "Invalid select "')
            return
       
        result = subprocess.run(['git', 'switch', line_content], capture_output=True, text=True)
        
        if len(result.stderr) > 0:
            self.vim.command('echo "{}"'.format(result.stderr[:-1]))
        self.update(1)

    @neovim.function('AutoGitMakeBranch')
    def make_branch(self, args):
        branch_name=self.vim.call('input', 'Enter branch name: ')
        result = subprocess.run(['git', 'branch',branch_name], capture_output=True, text=True)

        if len(result.stderr) > 0:
            self.vim.command('echo "{}"'.format(result.stderr))
        else:
            self.vim.command('echo "Branch was created "')
        self.update(1)


    @neovim.function('AutoGitCommit')
    def commit(self, args):
        commit_message = self.vim.call('input', 'Enter commit message: ')
        subprocess.run(['git', 'commit', '-m', commit_message])

        self.vim.command('echo "Committed with message: {}"'.format(commit_message))

        self.update(0)


    @neovim.function('AutoGitModify',sync=True)
    def modify(self, args):
        untracked_files, staging_files= self.git.status() 
        staging_files = [item.a_path for item in staging_files]
        line_number = self.vim.current.window.cursor[0]
        line_content = self.vim.current.buffer[line_number - 1]
        if line_content == '':
            return
        if line_content == 'Untracked files':
            self.git.git_add(line_content,True)
            self.update(0)
            return
        if line_content == 'Staging files':
            self.git.resotre(line_content, True)
            self.update(0)

        if line_content in staging_files:
            self.git.resotre(line_content, False)

        line_content = self.vim.current.buffer[line_number - 1][3:]
        line_content = line_content.replace('"',r"").replace(' ',r'\ ')
        files = [files[3:] for files in untracked_files] 
        if line_content in files:
            self.git.git_add(line_content,False) 

        self.update(0)
   

    @neovim.function('AutoGitUpdate')
    def update(self,buf):
        
        self.vim.command('setlocal modifiable')
        if buf == 0:
            untracked_files= subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
            staging_files= subprocess.run(['git', 'diff','--name-only', '--cached'], capture_output=True, text=True)
            current_branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True)
            l = untracked_files.stdout.split("\n")
            for i in l[:-1]:
                if  i[1] == ' ':
                    l.remove(i)

            untracked_files = '\n'.join(l)
            l = []
            self.vim.current.buffer[:] = self.buffer_status.format(current_branch.stdout.strip(), untracked_files, staging_files.stdout).strip().splitlines()
        if buf  == 1:
            result = subprocess.run(['git', 'branch','-a'], capture_output=True, text=True)
            current_branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True)
            result.stdout = result.stdout.replace('*',' ')
            self.vim.current.buffer[:] = self.buffer_branch.format(current_branch.stdout.strip(), result.stdout).strip().splitlines()
        
        self.vim.command('setlocal nomodifiable')
   
    

    @neovim.function('AutoGitPush')
    def push(self, args):
        current_branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True)
        result =  subprocess.run(['git', 'push','-u','origin',current_branch.stdout[:-1]], capture_output=True, text=True)
        if len(result.stderr) > 0:
            self.vim.command('echo "{}"'.format(result.stderr))
        else: 
            self.vim.command('echo "Pushed changes"')

        self.update(0)
    

    @neovim.function('AutoGitPull')
    def pull(self, args):

        result =  subprocess.run(['git', 'pull'], capture_output=True, text=True)
        
        if len(result.stderr) > 0:
            self.vim.command('echo "{}"'.format(result.stderr))
        else: 
            self.vim.command('echo "{}"'.format(result.stdout))


        self.update(0)